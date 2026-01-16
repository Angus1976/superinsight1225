#!/usr/bin/env node
/**
 * i18n Translation Key Bidirectional Completeness Check
 * 
 * This script compares translation keys between zh and en locale files
 * to ensure bidirectional completeness (every key in zh exists in en and vice versa).
 */

const fs = require('fs');
const path = require('path');

const localesDir = path.join(__dirname, '..', 'src', 'locales');
const zhDir = path.join(localesDir, 'zh');
const enDir = path.join(localesDir, 'en');

/**
 * Recursively extract all keys from a JSON object with dot notation
 */
function extractKeys(obj, prefix = '') {
  const keys = [];
  for (const key of Object.keys(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
      keys.push(...extractKeys(obj[key], fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys;
}

/**
 * Compare keys between two translation files
 */
function compareTranslationFiles(namespace) {
  const zhPath = path.join(zhDir, `${namespace}.json`);
  const enPath = path.join(enDir, `${namespace}.json`);
  
  const result = {
    namespace,
    zhExists: fs.existsSync(zhPath),
    enExists: fs.existsSync(enPath),
    missingInEn: [],
    missingInZh: [],
    zhKeyCount: 0,
    enKeyCount: 0,
  };
  
  if (!result.zhExists || !result.enExists) {
    return result;
  }
  
  try {
    const zhContent = JSON.parse(fs.readFileSync(zhPath, 'utf-8'));
    const enContent = JSON.parse(fs.readFileSync(enPath, 'utf-8'));
    
    const zhKeys = new Set(extractKeys(zhContent));
    const enKeys = new Set(extractKeys(enContent));
    
    result.zhKeyCount = zhKeys.size;
    result.enKeyCount = enKeys.size;
    
    // Find keys missing in English
    for (const key of zhKeys) {
      if (!enKeys.has(key)) {
        result.missingInEn.push(key);
      }
    }
    
    // Find keys missing in Chinese
    for (const key of enKeys) {
      if (!zhKeys.has(key)) {
        result.missingInZh.push(key);
      }
    }
  } catch (error) {
    result.error = error.message;
  }
  
  return result;
}

/**
 * Get all namespace names from the zh directory
 */
function getNamespaces() {
  const files = fs.readdirSync(zhDir);
  return files
    .filter(f => f.endsWith('.json'))
    .map(f => f.replace('.json', ''));
}

/**
 * Main function
 */
function main() {
  console.log('='.repeat(80));
  console.log('i18n Translation Key Bidirectional Completeness Check');
  console.log('='.repeat(80));
  console.log();
  
  const namespaces = getNamespaces();
  const results = [];
  let totalMissingInEn = 0;
  let totalMissingInZh = 0;
  
  for (const namespace of namespaces) {
    const result = compareTranslationFiles(namespace);
    results.push(result);
    totalMissingInEn += result.missingInEn.length;
    totalMissingInZh += result.missingInZh.length;
  }
  
  // Print summary
  console.log('SUMMARY');
  console.log('-'.repeat(80));
  console.log(`${'Namespace'.padEnd(20)} | ${'ZH Keys'.padEnd(10)} | ${'EN Keys'.padEnd(10)} | ${'Missing EN'.padEnd(12)} | ${'Missing ZH'.padEnd(12)}`);
  console.log('-'.repeat(80));
  
  for (const result of results) {
    const status = (result.missingInEn.length === 0 && result.missingInZh.length === 0) ? '✓' : '✗';
    console.log(
      `${status} ${result.namespace.padEnd(18)} | ${String(result.zhKeyCount).padEnd(10)} | ${String(result.enKeyCount).padEnd(10)} | ${String(result.missingInEn.length).padEnd(12)} | ${String(result.missingInZh.length).padEnd(12)}`
    );
  }
  
  console.log('-'.repeat(80));
  console.log(`Total: ${totalMissingInEn} keys missing in EN, ${totalMissingInZh} keys missing in ZH`);
  console.log();
  
  // Print detailed discrepancies
  const hasDiscrepancies = results.some(r => r.missingInEn.length > 0 || r.missingInZh.length > 0);
  
  if (hasDiscrepancies) {
    console.log('DETAILED DISCREPANCIES');
    console.log('='.repeat(80));
    
    for (const result of results) {
      if (result.missingInEn.length > 0 || result.missingInZh.length > 0) {
        console.log();
        console.log(`[${result.namespace}]`);
        
        if (result.missingInEn.length > 0) {
          console.log(`  Missing in EN (${result.missingInEn.length} keys):`);
          for (const key of result.missingInEn) {
            console.log(`    - ${key}`);
          }
        }
        
        if (result.missingInZh.length > 0) {
          console.log(`  Missing in ZH (${result.missingInZh.length} keys):`);
          for (const key of result.missingInZh) {
            console.log(`    - ${key}`);
          }
        }
      }
    }
  } else {
    console.log('✓ All translation files are bidirectionally complete!');
  }
  
  // Output JSON report for programmatic use
  const reportPath = path.join(__dirname, 'i18n-completeness-report.json');
  fs.writeFileSync(reportPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    summary: {
      totalNamespaces: namespaces.length,
      totalMissingInEn,
      totalMissingInZh,
      isComplete: totalMissingInEn === 0 && totalMissingInZh === 0,
    },
    results,
  }, null, 2));
  console.log();
  console.log(`Report saved to: ${reportPath}`);
  
  // Exit with error code if there are discrepancies
  process.exit(hasDiscrepancies ? 1 : 0);
}

main();
