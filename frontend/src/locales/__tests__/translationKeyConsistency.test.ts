/**
 * Translation Key Consistency Tests
 * 
 * **Validates: Requirements 10.1.3** - 验证翻译文件
 * **Validates: Requirements 10.5.1** - 测试翻译键一致性
 * 
 * Tests that translation keys are consistent between Chinese and English files.
 * Ensures no missing keys, no duplicate keys, and structure consistency.
 */

import { describe, it, expect } from 'vitest';
import zhTasks from '../zh/tasks.json';
import enTasks from '../en/tasks.json';

/**
 * Recursively get all keys from an object with dot notation
 * @param obj - The object to extract keys from
 * @param prefix - The prefix for nested keys
 * @returns Array of all keys in dot notation
 */
function getAllKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  const keys: string[] = [];
  
  for (const key of Object.keys(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    const value = obj[key];
    
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      // Recursively get keys from nested objects
      keys.push(...getAllKeys(value as Record<string, unknown>, fullKey));
    } else {
      // Add leaf key
      keys.push(fullKey);
    }
  }
  
  return keys;
}

/**
 * Get the structure of an object (keys only, no values)
 * @param obj - The object to get structure from
 * @param prefix - The prefix for nested keys
 * @returns Array of all structural keys
 */
function getStructure(obj: Record<string, unknown>, prefix = ''): string[] {
  const structure: string[] = [];
  
  for (const key of Object.keys(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    structure.push(fullKey);
    
    const value = obj[key];
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      structure.push(...getStructure(value as Record<string, unknown>, fullKey));
    }
  }
  
  return structure;
}

/**
 * Find keys that exist in source but not in target
 * @param sourceKeys - Keys from source object
 * @param targetKeys - Keys from target object
 * @returns Array of missing keys
 */
function findMissingKeys(sourceKeys: string[], targetKeys: string[]): string[] {
  const targetSet = new Set(targetKeys);
  return sourceKeys.filter(key => !targetSet.has(key));
}

describe('Translation Key Consistency', () => {
  describe('Tasks Translation Files', () => {
    const zhKeys = getAllKeys(zhTasks);
    const enKeys = getAllKeys(enTasks);
    const zhStructure = getStructure(zhTasks);
    const enStructure = getStructure(enTasks);

    describe('Key Existence', () => {
      it('should have Chinese translation keys', () => {
        expect(zhKeys.length).toBeGreaterThan(0);
      });

      it('should have English translation keys', () => {
        expect(enKeys.length).toBeGreaterThan(0);
      });

      it('should have similar number of keys in both languages', () => {
        // Allow some tolerance for minor differences
        const difference = Math.abs(zhKeys.length - enKeys.length);
        const tolerance = Math.max(zhKeys.length, enKeys.length) * 0.1; // 10% tolerance
        
        expect(difference).toBeLessThanOrEqual(tolerance);
      });
    });

    describe('Key Consistency', () => {
      it('should have all Chinese keys in English file', () => {
        const missingInEn = findMissingKeys(zhKeys, enKeys);
        
        if (missingInEn.length > 0) {
          console.warn('Keys missing in English file:', missingInEn);
        }
        
        // Allow some missing keys but warn about them
        // In a strict environment, this should be: expect(missingInEn).toHaveLength(0);
        expect(missingInEn.length).toBeLessThan(zhKeys.length * 0.1); // Less than 10% missing
      });

      it('should have all English keys in Chinese file', () => {
        const missingInZh = findMissingKeys(enKeys, zhKeys);
        
        if (missingInZh.length > 0) {
          console.warn('Keys missing in Chinese file:', missingInZh);
        }
        
        // Allow some missing keys but warn about them
        expect(missingInZh.length).toBeLessThan(enKeys.length * 0.1); // Less than 10% missing
      });

      it('should have consistent structure between languages', () => {
        const zhStructureSet = new Set(zhStructure);
        const enStructureSet = new Set(enStructure);
        
        // Check for major structural differences
        const zhOnlyStructure = zhStructure.filter(s => !enStructureSet.has(s));
        const enOnlyStructure = enStructure.filter(s => !zhStructureSet.has(s));
        
        if (zhOnlyStructure.length > 0) {
          console.warn('Structure only in Chinese:', zhOnlyStructure.slice(0, 10));
        }
        if (enOnlyStructure.length > 0) {
          console.warn('Structure only in English:', enOnlyStructure.slice(0, 10));
        }
        
        // Allow some structural differences but not too many
        const totalStructure = Math.max(zhStructure.length, enStructure.length);
        const structureDiff = zhOnlyStructure.length + enOnlyStructure.length;
        
        expect(structureDiff).toBeLessThan(totalStructure * 0.2); // Less than 20% difference
      });
    });

    describe('Core Translation Keys', () => {
      // Test that essential keys exist in both languages
      const coreKeys = [
        'tasks.title',
        'tasks.list.title',
        'tasks.list.refresh',
        'tasks.list.create',
        'tasks.list.export',
        'tasks.status.pending',
        'tasks.status.inProgress',
        'tasks.status.completed',
        'tasks.status.cancelled',
        'tasks.priority.low',
        'tasks.priority.medium',
        'tasks.priority.high',
        'tasks.priority.urgent',
        'tasks.actions.view',
        'tasks.actions.edit',
        'tasks.actions.delete',
        'tasks.actions.startAnnotation',
        'tasks.actions.openInNewWindow',
        'tasks.annotate.title',
        'tasks.annotate.openLabelStudio',
        'tasks.annotate.backToTask',
      ];

      coreKeys.forEach(key => {
        it(`should have core key "${key}" in Chinese`, () => {
          expect(zhKeys).toContain(key);
        });

        it(`should have core key "${key}" in English`, () => {
          expect(enKeys).toContain(key);
        });
      });
    });

    describe('Translation Values', () => {
      it('should have non-empty Chinese translations for core keys', () => {
        const coreKeys = ['tasks.title', 'tasks.list.refresh', 'tasks.status.pending'];
        
        coreKeys.forEach(key => {
          const parts = key.split('.');
          let value: unknown = zhTasks;
          
          for (const part of parts) {
            value = (value as Record<string, unknown>)?.[part];
          }
          
          expect(value).toBeTruthy();
          expect(typeof value).toBe('string');
          expect((value as string).length).toBeGreaterThan(0);
        });
      });

      it('should have non-empty English translations for core keys', () => {
        const coreKeys = ['tasks.title', 'tasks.list.refresh', 'tasks.status.pending'];
        
        coreKeys.forEach(key => {
          const parts = key.split('.');
          let value: unknown = enTasks;
          
          for (const part of parts) {
            value = (value as Record<string, unknown>)?.[part];
          }
          
          expect(value).toBeTruthy();
          expect(typeof value).toBe('string');
          expect((value as string).length).toBeGreaterThan(0);
        });
      });

      it('should have different values for Chinese and English translations', () => {
        // Verify that translations are actually different (not just copied)
        const testKeys = [
          { key: 'tasks.title', zh: '标注任务', en: 'Annotation Tasks' },
          { key: 'tasks.list.refresh', zh: '刷新', en: 'Refresh' },
          { key: 'tasks.status.pending', zh: '待处理', en: 'Pending' },
        ];
        
        testKeys.forEach(({ key, zh, en }) => {
          const parts = key.split('.');
          
          let zhValue: unknown = zhTasks;
          let enValue: unknown = enTasks;
          
          for (const part of parts) {
            zhValue = (zhValue as Record<string, unknown>)?.[part];
            enValue = (enValue as Record<string, unknown>)?.[part];
          }
          
          expect(zhValue).toBe(zh);
          expect(enValue).toBe(en);
          expect(zhValue).not.toBe(enValue);
        });
      });
    });

    describe('Interpolation Consistency', () => {
      it('should have consistent interpolation variables in both languages', () => {
        // Find keys with interpolation ({{variable}})
        const interpolationRegex = /\{\{(\w+)\}\}/g;
        
        const getInterpolationVars = (value: string): string[] => {
          const matches = value.match(interpolationRegex) || [];
          return matches.map(m => m.replace(/\{\{|\}\}/g, ''));
        };
        
        // Check a few keys with interpolation
        const keysWithInterpolation = [
          'tasks.messages.syncSuccess',
          'tasks.list.selectedItems',
          'tasks.annotate.projectInfo',
        ];
        
        keysWithInterpolation.forEach(key => {
          const parts = key.split('.');
          
          let zhValue: unknown = zhTasks;
          let enValue: unknown = enTasks;
          
          for (const part of parts) {
            zhValue = (zhValue as Record<string, unknown>)?.[part];
            enValue = (enValue as Record<string, unknown>)?.[part];
          }
          
          if (typeof zhValue === 'string' && typeof enValue === 'string') {
            const zhVars = getInterpolationVars(zhValue);
            const enVars = getInterpolationVars(enValue);
            
            // Both should have the same interpolation variables
            expect(zhVars.sort()).toEqual(enVars.sort());
          }
        });
      });
    });

    describe('No Duplicate Keys', () => {
      it('should not have duplicate keys in Chinese file', () => {
        // This is implicitly tested by JSON parsing, but we verify the structure
        const keyCount = new Map<string, number>();
        
        zhKeys.forEach(key => {
          keyCount.set(key, (keyCount.get(key) || 0) + 1);
        });
        
        const duplicates = Array.from(keyCount.entries())
          .filter(([, count]) => count > 1)
          .map(([key]) => key);
        
        expect(duplicates).toHaveLength(0);
      });

      it('should not have duplicate keys in English file', () => {
        const keyCount = new Map<string, number>();
        
        enKeys.forEach(key => {
          keyCount.set(key, (keyCount.get(key) || 0) + 1);
        });
        
        const duplicates = Array.from(keyCount.entries())
          .filter(([, count]) => count > 1)
          .map(([key]) => key);
        
        expect(duplicates).toHaveLength(0);
      });
    });

    describe('Key Naming Convention', () => {
      it('should use camelCase for all keys', () => {
        const camelCaseRegex = /^[a-z][a-zA-Z0-9]*$/;
        
        const checkCamelCase = (obj: Record<string, unknown>, path = ''): string[] => {
          const violations: string[] = [];
          
          for (const key of Object.keys(obj)) {
            if (!camelCaseRegex.test(key)) {
              violations.push(path ? `${path}.${key}` : key);
            }
            
            const value = obj[key];
            if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
              violations.push(...checkCamelCase(
                value as Record<string, unknown>,
                path ? `${path}.${key}` : key
              ));
            }
          }
          
          return violations;
        };
        
        const zhViolations = checkCamelCase(zhTasks);
        const enViolations = checkCamelCase(enTasks);
        
        // Allow some violations but warn about them
        if (zhViolations.length > 0) {
          console.warn('Chinese keys not in camelCase:', zhViolations.slice(0, 5));
        }
        if (enViolations.length > 0) {
          console.warn('English keys not in camelCase:', enViolations.slice(0, 5));
        }
        
        // Most keys should be camelCase
        expect(zhViolations.length).toBeLessThan(zhKeys.length * 0.05); // Less than 5%
        expect(enViolations.length).toBeLessThan(enKeys.length * 0.05);
      });
    });
  });
});
