#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Read translation files
const zhPath = path.join(__dirname, '../frontend/src/locales/zh/admin.json');
const enPath = path.join(__dirname, '../frontend/src/locales/en/admin.json');

const zh = JSON.parse(fs.readFileSync(zhPath, 'utf8'));
const en = JSON.parse(fs.readFileSync(enPath, 'utf8'));

// Required translation keys for Console page
const requiredKeys = [
  'console.title',
  'console.subtitle',
  'console.systemConfig',
  'console.systemStatus',
  'console.healthy',
  'console.unhealthy',
  'console.database',
  'console.cache',
  'console.storage',
  'console.normal',
  'console.abnormal',
  'console.tenantStats',
  'console.totalTenants',
  'console.activeTenants',
  'console.suspendedTenants',
  'console.disabledTenants',
  'console.active',
  'console.workspaceStats',
  'console.totalWorkspaces',
  'console.activeWorkspaces',
  'console.archivedWorkspaces',
  'console.userStats',
  'console.totalUsers',
  'console.activeToday',
  'console.activeThisWeek',
  'console.serviceStatus',
  'console.columns.serviceName',
  'console.columns.status',
  'console.columns.version',
  'console.columns.uptime',
  'console.columns.lastCheck',
  'console.status.running',
  'console.status.degraded',
  'console.status.stopped',
  'console.lastUpdated'
];

console.log('=== Console Translation Key Verification ===\n');

let allPresent = true;
let zhMissing = [];
let enMissing = [];

requiredKeys.forEach(key => {
  const parts = key.split('.');
  let zhValue = zh;
  let enValue = en;
  
  for (const part of parts) {
    zhValue = zhValue?.[part];
    enValue = enValue?.[part];
  }
  
  if (!zhValue) {
    console.log('❌ Missing in zh:', key);
    zhMissing.push(key);
    allPresent = false;
  } else {
    console.log('✓ zh:', key, '→', zhValue);
  }
  
  if (!enValue) {
    console.log('❌ Missing in en:', key);
    enMissing.push(key);
    allPresent = false;
  } else {
    console.log('✓ en:', key, '→', enValue);
  }
  console.log('');
});

console.log('\n=== Summary ===');
console.log('Total keys checked:', requiredKeys.length);
console.log('Missing in zh:', zhMissing.length);
console.log('Missing in en:', enMissing.length);

if (allPresent) {
  console.log('\n✅ SUCCESS: All console translation keys present in both languages');
  process.exit(0);
} else {
  console.log('\n❌ FAILURE: Some translation keys are missing');
  if (zhMissing.length > 0) {
    console.log('\nMissing in zh:', zhMissing.join(', '));
  }
  if (enMissing.length > 0) {
    console.log('Missing in en:', enMissing.join(', '));
  }
  process.exit(1);
}
