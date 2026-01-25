/**
 * Verify Translation Completeness
 * 
 * This script checks:
 * 1. All keys in zh/admin.json have corresponding keys in en/admin.json
 * 2. No values look like translation keys (contain dots, camelCase)
 * 3. No empty or missing translations
 */

const fs = require('fs');
const path = require('path');

// Translation key patterns that should NOT appear as values
const SUSPICIOUS_PATTERNS = [
  /^\w+\.\w+\.\w+$/,  // Exact pattern: word.word.word
  /^[a-z]+[A-Z]\w*\./,  // camelCase followed by dot
  /^(billingManagement|permissionConfig|quotaManagement|console|admin)\./,
];

function loadJSON(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(content);
  } catch (error) {
    console.error(`Error loading ${filePath}:`, error.message);
    return null;
  }
}

function getAllKeys(obj, prefix = '') {
  let keys = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      keys = keys.concat(getAllKeys(value, fullKey));
    } else {
      keys.push({ key: fullKey, value: value });
    }
  }
  return keys;
}

function looksLikeTranslationKey(value) {
  if (typeof value !== 'string') return false;
  return SUSPICIOUS_PATTERNS.some(pattern => pattern.test(value));
}

function checkTranslations() {
  console.log('🔍 Verifying Translation Completeness...\n');
  console.log('='.repeat(60));

  const zhPath = path.join(__dirname, '../frontend/src/locales/zh/admin.json');
  const enPath = path.join(__dirname, '../frontend/src/locales/en/admin.json');

  // Load translation files
  const zhData = loadJSON(zhPath);
  const enData = loadJSON(enPath);

  if (!zhData || !enData) {
    console.error('❌ Failed to load translation files');
    return 1;
  }

  console.log('✅ Translation files loaded successfully\n');

  // Get all keys
  const zhKeys = getAllKeys(zhData);
  const enKeys = getAllKeys(enData);

  console.log(`📊 Statistics:`);
  console.log(`   Chinese keys: ${zhKeys.length}`);
  console.log(`   English keys: ${enKeys.length}`);
  console.log();

  let hasIssues = false;

  // Check 1: Missing keys
  console.log('1️⃣  Checking for missing keys...');
  const zhKeySet = new Set(zhKeys.map(k => k.key));
  const enKeySet = new Set(enKeys.map(k => k.key));

  const missingInEn = zhKeys.filter(k => !enKeySet.has(k.key));
  const missingInZh = enKeys.filter(k => !zhKeySet.has(k.key));

  if (missingInEn.length > 0) {
    console.log(`   ❌ ${missingInEn.length} keys missing in English:`);
    missingInEn.slice(0, 10).forEach(k => {
      console.log(`      - ${k.key}`);
    });
    if (missingInEn.length > 10) {
      console.log(`      ... and ${missingInEn.length - 10} more`);
    }
    hasIssues = true;
  } else {
    console.log('   ✅ All Chinese keys have English translations');
  }

  if (missingInZh.length > 0) {
    console.log(`   ❌ ${missingInZh.length} keys missing in Chinese:`);
    missingInZh.slice(0, 10).forEach(k => {
      console.log(`      - ${k.key}`);
    });
    if (missingInZh.length > 10) {
      console.log(`      ... and ${missingInZh.length - 10} more`);
    }
    hasIssues = true;
  } else {
    console.log('   ✅ All English keys have Chinese translations');
  }
  console.log();

  // Check 2: Values that look like translation keys
  console.log('2️⃣  Checking for suspicious values (raw translation keys)...');
  
  const suspiciousZh = zhKeys.filter(k => looksLikeTranslationKey(k.value));
  const suspiciousEn = enKeys.filter(k => looksLikeTranslationKey(k.value));

  if (suspiciousZh.length > 0) {
    console.log(`   ❌ ${suspiciousZh.length} suspicious values in Chinese:`);
    suspiciousZh.forEach(k => {
      console.log(`      - ${k.key}: "${k.value}"`);
    });
    hasIssues = true;
  } else {
    console.log('   ✅ No suspicious values in Chinese');
  }

  if (suspiciousEn.length > 0) {
    console.log(`   ❌ ${suspiciousEn.length} suspicious values in English:`);
    suspiciousEn.forEach(k => {
      console.log(`      - ${k.key}: "${k.value}"`);
    });
    hasIssues = true;
  } else {
    console.log('   ✅ No suspicious values in English');
  }
  console.log();

  // Check 3: Empty values
  console.log('3️⃣  Checking for empty values...');
  
  const emptyZh = zhKeys.filter(k => !k.value || k.value.trim() === '');
  const emptyEn = enKeys.filter(k => !k.value || k.value.trim() === '');

  if (emptyZh.length > 0) {
    console.log(`   ❌ ${emptyZh.length} empty values in Chinese:`);
    emptyZh.forEach(k => {
      console.log(`      - ${k.key}`);
    });
    hasIssues = true;
  } else {
    console.log('   ✅ No empty values in Chinese');
  }

  if (emptyEn.length > 0) {
    console.log(`   ❌ ${emptyEn.length} empty values in English:`);
    emptyEn.forEach(k => {
      console.log(`      - ${k.key}`);
    });
    hasIssues = true;
  } else {
    console.log('   ✅ No empty values in English');
  }
  console.log();

  // Summary
  console.log('='.repeat(60));
  console.log('📊 SUMMARY');
  console.log('='.repeat(60));
  
  if (!hasIssues) {
    console.log('✅ ALL CHECKS PASSED');
    console.log('   - All keys are present in both languages');
    console.log('   - No suspicious values found');
    console.log('   - No empty values found');
    console.log('\n✅ Translation files are ready for use!');
    return 0;
  } else {
    console.log('❌ ISSUES FOUND');
    if (missingInEn.length > 0 || missingInZh.length > 0) {
      console.log(`   - Missing keys: ${missingInEn.length + missingInZh.length}`);
    }
    if (suspiciousZh.length > 0 || suspiciousEn.length > 0) {
      console.log(`   - Suspicious values: ${suspiciousZh.length + suspiciousEn.length}`);
    }
    if (emptyZh.length > 0 || emptyEn.length > 0) {
      console.log(`   - Empty values: ${emptyZh.length + emptyEn.length}`);
    }
    console.log('\n❌ Please fix the issues above before deployment!');
    return 1;
  }
}

// Run the checks
const exitCode = checkTranslations();
process.exit(exitCode);
