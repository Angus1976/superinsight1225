/**
 * Billing Management Translation Test Script
 * Tests all translation keys used in the Billing Management page
 */

const fs = require('fs');
const path = require('path');

// Load the admin.json translation file
const adminJsonPath = path.join(__dirname, '../frontend/src/locales/zh/admin.json');
const adminTranslations = JSON.parse(fs.readFileSync(adminJsonPath, 'utf-8'));

// Define all translation keys used in BillingManagement.tsx
const requiredKeys = [
  // Title
  'billingManagement.title',
  
  // Summary section
  'billingManagement.summary.monthlyRevenue',
  'billingManagement.summary.paid',
  'billingManagement.summary.pending',
  'billingManagement.summary.overdue',
  'billingManagement.summary.pageTotal',
  
  // Columns
  'billingManagement.columns.tenant',
  'billingManagement.columns.period',
  'billingManagement.columns.storage',
  'billingManagement.columns.api',
  'billingManagement.columns.user',
  'billingManagement.columns.total',
  'billingManagement.columns.status',
  'billingManagement.columns.actions',
  
  // Status
  'billingManagement.status.pending',
  'billingManagement.status.paid',
  'billingManagement.status.overdue',
  
  // Actions
  'billingManagement.actions.details',
  'billingManagement.actions.download',
  
  // Units
  'billingManagement.unit.calls',
  'billingManagement.unit.users',
  'billingManagement.unit.currency',
  
  // Export
  'billingManagement.export.exporting',
  'billingManagement.export.csv',
  'billingManagement.export.excel',
  'billingManagement.export.pdf',
  
  // Tabs
  'billingManagement.tabs.all',
  'billingManagement.tabs.pending',
  'billingManagement.tabs.paid',
  'billingManagement.tabs.overdue',
  
  // Charts
  'billingManagement.charts.storageDistribution',
  'billingManagement.charts.apiTrend',
  'billingManagement.charts.revenueTrend',
  
  // Pagination
  'billingManagement.pagination.total',
  
  // Common keys
  'common.refresh',
];

// Helper function to get nested value from object
function getNestedValue(obj, path) {
  return path.split('.').reduce((current, key) => current?.[key], obj);
}

// Test results
const results = {
  passed: [],
  failed: [],
  warnings: []
};

console.log('='.repeat(80));
console.log('BILLING MANAGEMENT TRANSLATION TEST');
console.log('='.repeat(80));
console.log();

// Test each required key
requiredKeys.forEach(key => {
  const value = getNestedValue(adminTranslations, key);
  
  if (value === undefined) {
    results.failed.push({
      key,
      issue: 'Key not found in translation file'
    });
  } else if (value === '') {
    results.warnings.push({
      key,
      issue: 'Key exists but value is empty'
    });
  } else if (key.includes(value)) {
    results.warnings.push({
      key,
      value,
      issue: 'Value might be a raw key (contains the key name)'
    });
  } else {
    results.passed.push({
      key,
      value
    });
  }
});

// Print results
console.log(`✅ PASSED: ${results.passed.length}/${requiredKeys.length}`);
console.log(`❌ FAILED: ${results.failed.length}/${requiredKeys.length}`);
console.log(`⚠️  WARNINGS: ${results.warnings.length}/${requiredKeys.length}`);
console.log();

if (results.failed.length > 0) {
  console.log('❌ MISSING TRANSLATION KEYS:');
  console.log('-'.repeat(80));
  results.failed.forEach(({ key, issue }) => {
    console.log(`  • ${key}`);
    console.log(`    Issue: ${issue}`);
  });
  console.log();
}

if (results.warnings.length > 0) {
  console.log('⚠️  WARNINGS:');
  console.log('-'.repeat(80));
  results.warnings.forEach(({ key, value, issue }) => {
    console.log(`  • ${key}`);
    if (value) console.log(`    Value: "${value}"`);
    console.log(`    Issue: ${issue}`);
  });
  console.log();
}

if (results.passed.length > 0) {
  console.log('✅ VERIFIED TRANSLATIONS (Sample):');
  console.log('-'.repeat(80));
  results.passed.slice(0, 10).forEach(({ key, value }) => {
    console.log(`  • ${key}: "${value}"`);
  });
  if (results.passed.length > 10) {
    console.log(`  ... and ${results.passed.length - 10} more`);
  }
  console.log();
}

// Check billingManagement structure
console.log('📋 BILLING MANAGEMENT STRUCTURE:');
console.log('-'.repeat(80));
if (adminTranslations.billingManagement) {
  console.log('billingManagement object exists:');
  console.log(JSON.stringify(adminTranslations.billingManagement, null, 2));
} else {
  console.log('❌ billingManagement object not found!');
}
console.log();

// Summary
console.log('='.repeat(80));
console.log('TEST SUMMARY');
console.log('='.repeat(80));

if (results.failed.length === 0 && results.warnings.length === 0) {
  console.log('✅ ALL TESTS PASSED!');
  console.log('All required translation keys are present and valid.');
  process.exit(0);
} else {
  console.log('❌ TESTS FAILED!');
  if (results.failed.length > 0) {
    console.log(`   ${results.failed.length} missing translation keys`);
  }
  if (results.warnings.length > 0) {
    console.log(`   ${results.warnings.length} warnings`);
  }
  console.log();
  console.log('ACTION REQUIRED:');
  console.log('1. Add missing translation keys to frontend/src/locales/zh/admin.json');
  console.log('2. Verify warning items are intentional');
  console.log('3. Re-run this test to verify fixes');
  process.exit(1);
}
