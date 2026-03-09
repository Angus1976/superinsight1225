/**
 * Property Test: Internationalization Completeness
 *
 * **Validates: Requirements 11.5, 19.2, 19.3, 19.4, 19.5, 19.6**
 *
 * Property 26: For all UI components, every user-visible text element must use
 * the t() function with valid translation keys, and both Chinese and English
 * translation files must have identical key structures.
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import * as fs from 'fs';
import * as path from 'path';

// ============================================================================
// Types
// ============================================================================

interface TranslationFile {
  path: string;
  content: Record<string, any>;
  keys: Set<string>;
}

interface ComponentFile {
  path: string;
  content: string;
}

interface HardcodedText {
  file: string;
  line: number;
  text: string;
  context: string;
}

// ============================================================================
// Translation File Utilities
// ============================================================================

/**
 * Load a translation JSON file and extract all keys
 */
function loadTranslationFile(filePath: string): TranslationFile {
  const absolutePath = path.resolve(__dirname, '..', filePath);
  const content = JSON.parse(fs.readFileSync(absolutePath, 'utf-8'));
  const keys = extractAllKeys(content);
  
  return {
    path: filePath,
    content,
    keys,
  };
}

/**
 * Recursively extract all keys from a nested translation object
 */
function extractAllKeys(obj: Record<string, any>, prefix = ''): Set<string> {
  const keys = new Set<string>();
  
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    keys.add(fullKey);
    
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      const nestedKeys = extractAllKeys(value, fullKey);
      nestedKeys.forEach(k => keys.add(k));
    }
  }
  
  return keys;
}

/**
 * Compare two sets of keys and return differences
 */
function compareKeySets(keys1: Set<string>, keys2: Set<string>): {
  onlyInFirst: string[];
  onlyInSecond: string[];
  common: string[];
} {
  const onlyInFirst = Array.from(keys1).filter(k => !keys2.has(k));
  const onlyInSecond = Array.from(keys2).filter(k => !keys1.has(k));
  const common = Array.from(keys1).filter(k => keys2.has(k));
  
  return { onlyInFirst, onlyInSecond, common };
}

// ============================================================================
// Component Analysis Utilities
// ============================================================================

/**
 * Load all component files from a directory recursively
 */
function loadComponentFiles(dirPath: string): ComponentFile[] {
  const absolutePath = path.resolve(__dirname, '..', dirPath);
  const files: ComponentFile[] = [];
  
  function traverse(currentPath: string) {
    if (!fs.existsSync(currentPath)) {
      return;
    }
    
    const entries = fs.readdirSync(currentPath, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(currentPath, entry.name);
      
      if (entry.isDirectory() && entry.name !== '__tests__' && entry.name !== 'node_modules') {
        traverse(fullPath);
      } else if (entry.isFile() && /\.(tsx|jsx)$/.test(entry.name)) {
        const content = fs.readFileSync(fullPath, 'utf-8');
        const relativePath = path.relative(path.resolve(__dirname, '..'), fullPath);
        files.push({ path: relativePath, content });
      }
    }
  }
  
  traverse(absolutePath);
  return files;
}

/**
 * Find hardcoded Chinese or English text in JSX that should use t()
 * This is a heuristic check - it looks for:
 * 1. String literals in JSX children that contain Chinese characters or common English UI words
 * 2. String literals in common UI props (title, placeholder, label, etc.)
 */
function findHardcodedText(file: ComponentFile): HardcodedText[] {
  const hardcoded: HardcodedText[] = [];
  const lines = file.content.split('\n');
  
  // Patterns to detect hardcoded text
  const chinesePattern = /[\u4e00-\u9fa5]/; // Chinese characters
  const uiPropsPattern = /(title|placeholder|label|content|message|description|text|alt|aria-label)\s*=\s*["']([^"']+)["']/g;
  
  // Pattern to detect JSX children with hardcoded text (not using t())
  // This is simplified - a full AST parser would be more accurate
  const jsxChildPattern = />([^<{]*[\u4e00-\u9fa5][^<{]*)</g;
  
  lines.forEach((line, index) => {
    const lineNumber = index + 1;
    
    // Skip comments and imports
    if (line.trim().startsWith('//') || line.trim().startsWith('/*') || line.trim().startsWith('import')) {
      return;
    }
    
    // Skip lines that already use t()
    if (line.includes('t(') || line.includes('useTranslation')) {
      return;
    }
    
    // Check for hardcoded Chinese in JSX children
    let match;
    while ((match = jsxChildPattern.exec(line)) !== null) {
      const text = match[1].trim();
      if (text && !text.startsWith('{') && chinesePattern.test(text)) {
        hardcoded.push({
          file: file.path,
          line: lineNumber,
          text,
          context: line.trim(),
        });
      }
    }
    
    // Check for hardcoded text in UI props
    while ((match = uiPropsPattern.exec(line)) !== null) {
      const propName = match[1];
      const propValue = match[2];
      
      // Check if it contains Chinese or common English UI words
      if (chinesePattern.test(propValue) || /^(Save|Cancel|Delete|Edit|Create|Submit|Search|Filter|Export|Import|Close|Back|Next|Previous|Confirm|Reset|View|Add|Remove|Update|Upload|Download)$/i.test(propValue)) {
        hardcoded.push({
          file: file.path,
          line: lineNumber,
          text: propValue,
          context: line.trim(),
        });
      }
    }
  });
  
  return hardcoded;
}

/**
 * Extract all t() function calls from a component
 */
function extractTranslationKeys(file: ComponentFile): string[] {
  const keys: string[] = [];
  
  // Pattern to match t('key') or t("key")
  // More precise: must have t( followed by quote, then key, then quote and closing paren
  const tFunctionPattern = /\bt\s*\(\s*['"]([^'"]+)['"]\s*\)/g;
  
  let match;
  while ((match = tFunctionPattern.exec(file.content)) !== null) {
    const key = match[1];
    
    // Skip date format strings (YYYY-MM-DD, etc.)
    if (/^[YMDHmsA\-\/\s:]+$/.test(key)) {
      continue;
    }
    
    // Skip single letters or very short keys that are likely not translation keys
    if (key.length < 3) {
      continue;
    }
    
    keys.push(key);
  }
  
  return keys;
}

// ============================================================================
// Property Tests
// ============================================================================

describe('Property 26: Internationalization Completeness', () => {
  const zhTranslations = loadTranslationFile('locales/zh/dataLifecycle.json');
  const enTranslations = loadTranslationFile('locales/en/dataLifecycle.json');
  const dataLifecycleComponents = loadComponentFiles('components/DataLifecycle');
  const dataLifecyclePages = loadComponentFiles('pages/DataLifecycle');
  const allComponents = [...dataLifecycleComponents, ...dataLifecyclePages];

  it('Chinese and English translation files have identical key structures', () => {
    const { onlyInFirst, onlyInSecond } = compareKeySets(
      zhTranslations.keys,
      enTranslations.keys
    );

    // Both files should have exactly the same keys
    expect(onlyInFirst).toEqual([]);
    expect(onlyInSecond).toEqual([]);
    
    // Verify they have the same number of keys
    expect(zhTranslations.keys.size).toBe(enTranslations.keys.size);
  });

  it('all translation keys used in components exist in translation files', () => {
    const missingKeys: { file: string; key: string }[] = [];
    
    for (const component of allComponents) {
      const usedKeys = extractTranslationKeys(component);
      
      for (const key of usedKeys) {
        // Remove namespace prefix if present (e.g., 'dataLifecycle.tempData.title' -> 'tempData.title')
        const normalizedKey = key.replace(/^dataLifecycle\./, '');
        
        if (!zhTranslations.keys.has(normalizedKey) && !zhTranslations.keys.has(key)) {
          missingKeys.push({ file: component.path, key });
        }
      }
    }
    
    if (missingKeys.length > 0) {
      console.error('Missing translation keys:', missingKeys);
    }
    
    expect(missingKeys).toEqual([]);
  });

  it('components do not contain hardcoded Chinese or English UI text', () => {
    const allHardcodedText: HardcodedText[] = [];
    
    for (const component of allComponents) {
      const hardcoded = findHardcodedText(component);
      allHardcodedText.push(...hardcoded);
    }
    
    if (allHardcodedText.length > 0) {
      console.error('Found hardcoded text in components:');
      allHardcodedText.forEach(item => {
        console.error(`  ${item.file}:${item.line} - "${item.text}"`);
        console.error(`    Context: ${item.context}`);
      });
    }
    
    expect(allHardcodedText).toEqual([]);
  });

  it('translation values are non-empty strings', () => {
    const emptyValues: string[] = [];
    
    function checkValues(obj: Record<string, any>, prefix = '') {
      for (const [key, value] of Object.entries(obj)) {
        const fullKey = prefix ? `${prefix}.${key}` : key;
        
        if (typeof value === 'string') {
          if (value.trim() === '') {
            emptyValues.push(fullKey);
          }
        } else if (typeof value === 'object' && value !== null) {
          checkValues(value, fullKey);
        }
      }
    }
    
    checkValues(zhTranslations.content);
    checkValues(enTranslations.content);
    
    expect(emptyValues).toEqual([]);
  });

  it('property: adding a key to one translation file requires adding it to the other', () => {
    // This property test generates random translation keys and verifies
    // that the key structure validation would catch missing keys
    
    const translationKeyArb = fc.record({
      section: fc.constantFrom('tempData', 'sampleLibrary', 'review', 'annotationTask', 'enhancement', 'aiTrial'),
      subsection: fc.constantFrom('title', 'description', 'columns', 'actions', 'messages', 'status'),
      key: fc.stringMatching(/^[a-zA-Z][a-zA-Z0-9]*$/),
    });
    
    fc.assert(
      fc.property(translationKeyArb, (keySpec) => {
        const fullKey = `${keySpec.section}.${keySpec.subsection}.${keySpec.key}`;
        
        // If a key exists in one file, it must exist in the other
        const inZh = zhTranslations.keys.has(fullKey);
        const inEn = enTranslations.keys.has(fullKey);
        
        // Either both have it or neither has it
        expect(inZh).toBe(inEn);
      }),
      { numRuns: 100 }
    );
  });

  it('property: translation key paths are consistent across languages', () => {
    // Generate arbitrary paths through the translation object structure
    const pathArb = fc.array(
      fc.stringMatching(/^[a-zA-Z][a-zA-Z0-9]*$/),
      { minLength: 1, maxLength: 5 }
    );
    
    fc.assert(
      fc.property(pathArb, (pathParts) => {
        const key = pathParts.join('.');
        
        // Helper to check if a path exists in a nested object
        function hasPath(obj: any, parts: string[]): boolean {
          let current = obj;
          for (const part of parts) {
            if (typeof current !== 'object' || current === null || !(part in current)) {
              return false;
            }
            current = current[part];
          }
          return true;
        }
        
        const zhHasPath = hasPath(zhTranslations.content, pathParts);
        const enHasPath = hasPath(enTranslations.content, pathParts);
        
        // Both should have the same structure
        expect(zhHasPath).toBe(enHasPath);
      }),
      { numRuns: 200 }
    );
  });

  it('property: all leaf values in translation files are strings', () => {
    function checkLeafTypes(obj: any, path: string[] = []): void {
      for (const [key, value] of Object.entries(obj)) {
        const currentPath = [...path, key];
        
        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
          checkLeafTypes(value, currentPath);
        } else {
          // Leaf value must be a string
          expect(typeof value).toBe('string');
        }
      }
    }
    
    checkLeafTypes(zhTranslations.content);
    checkLeafTypes(enTranslations.content);
  });
});
