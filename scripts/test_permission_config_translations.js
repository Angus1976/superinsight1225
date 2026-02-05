/**
 * Permission Config Page Translation Test
 * 
 * Tests Requirements 6.2 and 6.3:
 * - All translations display correctly
 * - Browser console clean (no i18n warnings)
 * 
 * Test Coverage:
 * - Page title and subtitle
 * - Role names (owner, admin, member, guest)
 * - Permission categories (workspace, member, project, annotation)
 * - All permission labels and descriptions
 * - API permission descriptions
 * - Table headers
 * - Tab labels
 * - Alert messages
 * - Button labels
 * - Placeholders
 * - Stats messages
 */

const fs = require('fs');
const path = require('path');

// Load translation file
const translationPath = path.join(__dirname, '../frontend/src/locales/zh/admin.json');
const translations = JSON.parse(fs.readFileSync(translationPath, 'utf8'));

// Test results
const results = {
  passed: [],
  failed: [],
  warnings: []
};

// Helper function to check if a key exists
function checkKey(keyPath, description) {
  const keys = keyPath.split('.');
  let current = translations;
  
  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = current[key];
    } else {
      results.failed.push({
        key: keyPath,
        description,
        error: `Missing translation key: ${keyPath}`
      });
      return false;
    }
  }
  
  if (typeof current === 'string' && current.trim().length > 0) {
    results.passed.push({
      key: keyPath,
      description,
      value: current
    });
    return true;
  } else {
    results.failed.push({
      key: keyPath,
      description,
      error: `Empty or invalid translation value for: ${keyPath}`
    });
    return false;
  }
}

console.log('🧪 Testing Permission Config Page Translations...\n');

// Test 1: Page Header
console.log('📋 Test 1: Page Header');
checkKey('permissionConfig.title', 'Page title');
checkKey('permissionConfig.subtitle', 'Page subtitle');

// Test 2: Role Names
console.log('\n👥 Test 2: Role Names');
checkKey('permissionConfig.roles.owner', 'Owner role');
checkKey('permissionConfig.roles.admin', 'Admin role');
checkKey('permissionConfig.roles.member', 'Member role');
checkKey('permissionConfig.roles.guest', 'Guest role');

// Test 3: Workspace Permissions
console.log('\n🏢 Test 3: Workspace Permissions');
checkKey('permissionConfig.permissions.workspace.title', 'Workspace section title');
checkKey('permissionConfig.permissions.workspace.create', 'Create workspace permission');
checkKey('permissionConfig.permissions.workspace.createDesc', 'Create workspace description');
checkKey('permissionConfig.permissions.workspace.read', 'Read workspace permission');
checkKey('permissionConfig.permissions.workspace.readDesc', 'Read workspace description');
checkKey('permissionConfig.permissions.workspace.update', 'Update workspace permission');
checkKey('permissionConfig.permissions.workspace.updateDesc', 'Update workspace description');
checkKey('permissionConfig.permissions.workspace.delete', 'Delete workspace permission');
checkKey('permissionConfig.permissions.workspace.deleteDesc', 'Delete workspace description');
checkKey('permissionConfig.permissions.workspace.archive', 'Archive workspace permission');
checkKey('permissionConfig.permissions.workspace.archiveDesc', 'Archive workspace description');

// Test 4: Member Permissions
console.log('\n👤 Test 4: Member Permissions');
checkKey('permissionConfig.permissions.member.title', 'Member section title');
checkKey('permissionConfig.permissions.member.invite', 'Invite member permission');
checkKey('permissionConfig.permissions.member.inviteDesc', 'Invite member description');
checkKey('permissionConfig.permissions.member.add', 'Add member permission');
checkKey('permissionConfig.permissions.member.addDesc', 'Add member description');
checkKey('permissionConfig.permissions.member.remove', 'Remove member permission');
checkKey('permissionConfig.permissions.member.removeDesc', 'Remove member description');
checkKey('permissionConfig.permissions.member.role', 'Modify role permission');
checkKey('permissionConfig.permissions.member.roleDesc', 'Modify role description');

// Test 5: Project Permissions
console.log('\n📁 Test 5: Project Permissions');
checkKey('permissionConfig.permissions.project.title', 'Project section title');
checkKey('permissionConfig.permissions.project.create', 'Create project permission');
checkKey('permissionConfig.permissions.project.createDesc', 'Create project description');
checkKey('permissionConfig.permissions.project.read', 'Read project permission');
checkKey('permissionConfig.permissions.project.readDesc', 'Read project description');
checkKey('permissionConfig.permissions.project.update', 'Update project permission');
checkKey('permissionConfig.permissions.project.updateDesc', 'Update project description');
checkKey('permissionConfig.permissions.project.delete', 'Delete project permission');
checkKey('permissionConfig.permissions.project.deleteDesc', 'Delete project description');
checkKey('permissionConfig.permissions.project.export', 'Export project permission');
checkKey('permissionConfig.permissions.project.exportDesc', 'Export project description');

// Test 6: Annotation Permissions
console.log('\n✏️ Test 6: Annotation Permissions');
checkKey('permissionConfig.permissions.annotation.title', 'Annotation section title');
checkKey('permissionConfig.permissions.annotation.create', 'Create annotation permission');
checkKey('permissionConfig.permissions.annotation.createDesc', 'Create annotation description');
checkKey('permissionConfig.permissions.annotation.read', 'Read annotation permission');
checkKey('permissionConfig.permissions.annotation.readDesc', 'Read annotation description');
checkKey('permissionConfig.permissions.annotation.update', 'Update annotation permission');
checkKey('permissionConfig.permissions.annotation.updateDesc', 'Update annotation description');
checkKey('permissionConfig.permissions.annotation.delete', 'Delete annotation permission');
checkKey('permissionConfig.permissions.annotation.deleteDesc', 'Delete annotation description');
checkKey('permissionConfig.permissions.annotation.review', 'Review annotation permission');
checkKey('permissionConfig.permissions.annotation.reviewDesc', 'Review annotation description');

// Test 7: API Permissions
console.log('\n🔌 Test 7: API Permissions');
checkKey('permissionConfig.apiPermissions.tenants', 'Tenants API description');
checkKey('permissionConfig.apiPermissions.workspaces', 'Workspaces API description');
checkKey('permissionConfig.apiPermissions.members', 'Members API description');
checkKey('permissionConfig.apiPermissions.projects', 'Projects API description');
checkKey('permissionConfig.apiPermissions.annotations', 'Annotations API description');
checkKey('permissionConfig.apiPermissions.quotas', 'Quotas API description');
checkKey('permissionConfig.apiPermissions.shares', 'Shares API description');
checkKey('permissionConfig.apiPermissions.admin', 'Admin API description');

// Test 8: Table Headers
console.log('\n📊 Test 8: Table Headers');
checkKey('permissionConfig.table.permission', 'Permission column header');
checkKey('permissionConfig.apiTable.endpoint', 'API endpoint column header');
checkKey('permissionConfig.apiTable.description', 'API description column header');
checkKey('permissionConfig.apiTable.methods', 'API methods column header');
checkKey('permissionConfig.apiTable.roles', 'API roles column header');

// Test 9: Tab Labels
console.log('\n📑 Test 9: Tab Labels');
checkKey('permissionConfig.tabs.matrix', 'Matrix tab label');
checkKey('permissionConfig.tabs.api', 'API tab label');
checkKey('permissionConfig.tabs.roles', 'Roles tab label');

// Test 10: Alert Messages
console.log('\n⚠️ Test 10: Alert Messages');
checkKey('permissionConfig.alert.title', 'Alert title');
checkKey('permissionConfig.alert.description', 'Alert description');

// Test 11: Buttons
console.log('\n🔘 Test 11: Buttons');
checkKey('permissionConfig.buttons.reset', 'Reset button');
checkKey('permissionConfig.buttons.save', 'Save button');

// Test 12: Placeholders
console.log('\n💬 Test 12: Placeholders');
checkKey('permissionConfig.placeholders.selectTenant', 'Select tenant placeholder');

// Test 13: Messages
console.log('\n💬 Test 13: Messages');
checkKey('permissionConfig.saveSuccess', 'Save success message');
checkKey('permissionConfig.resetSuccess', 'Reset success message');
checkKey('permissionConfig.ownerPermissionImmutable', 'Owner permission immutable message');

// Test 14: Stats
console.log('\n📈 Test 14: Stats');
checkKey('permissionConfig.stats.permissionCount', 'Permission count stat');

// Generate report
console.log('\n' + '='.repeat(80));
console.log('📊 TEST SUMMARY');
console.log('='.repeat(80));

console.log(`\n✅ Passed: ${results.passed.length}`);
console.log(`❌ Failed: ${results.failed.length}`);
console.log(`⚠️  Warnings: ${results.warnings.length}`);

if (results.failed.length > 0) {
  console.log('\n❌ FAILED TESTS:');
  results.failed.forEach(item => {
    console.log(`  - ${item.description}`);
    console.log(`    Key: ${item.key}`);
    console.log(`    Error: ${item.error}`);
  });
}

if (results.warnings.length > 0) {
  console.log('\n⚠️  WARNINGS:');
  results.warnings.forEach(item => {
    console.log(`  - ${item.description}`);
    console.log(`    Key: ${item.key}`);
    console.log(`    Warning: ${item.warning}`);
  });
}

// Write detailed report
const reportPath = path.join(__dirname, '../TASK_5.4_PERMISSION_CONFIG_TEST_REPORT.md');
const report = `# Permission Config Page Translation Test Report

**Test Date**: ${new Date().toISOString()}
**Test File**: frontend/src/pages/Admin/PermissionConfig.tsx
**Translation File**: frontend/src/locales/zh/admin.json

## Test Summary

- ✅ **Passed**: ${results.passed.length}
- ❌ **Failed**: ${results.failed.length}
- ⚠️  **Warnings**: ${results.warnings.length}

## Test Coverage

### 1. Page Header
- Page title: ${results.passed.find(r => r.key === 'permissionConfig.title') ? '✅' : '❌'}
- Page subtitle: ${results.passed.find(r => r.key === 'permissionConfig.subtitle') ? '✅' : '❌'}

### 2. Role Names (4 roles)
${['owner', 'admin', 'member', 'guest'].map(role => 
  `- ${role}: ${results.passed.find(r => r.key === `permissionConfig.roles.${role}`) ? '✅' : '❌'}`
).join('\n')}

### 3. Workspace Permissions (5 permissions + 5 descriptions)
${['create', 'read', 'update', 'delete', 'archive'].map(perm => 
  `- ${perm}: ${results.passed.find(r => r.key === `permissionConfig.permissions.workspace.${perm}`) ? '✅' : '❌'} / ${results.passed.find(r => r.key === `permissionConfig.permissions.workspace.${perm}Desc`) ? '✅' : '❌'}`
).join('\n')}

### 4. Member Permissions (4 permissions + 4 descriptions)
${['invite', 'add', 'remove', 'role'].map(perm => 
  `- ${perm}: ${results.passed.find(r => r.key === `permissionConfig.permissions.member.${perm}`) ? '✅' : '❌'} / ${results.passed.find(r => r.key === `permissionConfig.permissions.member.${perm}Desc`) ? '✅' : '❌'}`
).join('\n')}

### 5. Project Permissions (5 permissions + 5 descriptions)
${['create', 'read', 'update', 'delete', 'export'].map(perm => 
  `- ${perm}: ${results.passed.find(r => r.key === `permissionConfig.permissions.project.${perm}`) ? '✅' : '❌'} / ${results.passed.find(r => r.key === `permissionConfig.permissions.project.${perm}Desc`) ? '✅' : '❌'}`
).join('\n')}

### 6. Annotation Permissions (5 permissions + 5 descriptions)
${['create', 'read', 'update', 'delete', 'review'].map(perm => 
  `- ${perm}: ${results.passed.find(r => r.key === `permissionConfig.permissions.annotation.${perm}`) ? '✅' : '❌'} / ${results.passed.find(r => r.key === `permissionConfig.permissions.annotation.${perm}Desc`) ? '✅' : '❌'}`
).join('\n')}

### 7. API Permissions (8 endpoints)
${['tenants', 'workspaces', 'members', 'projects', 'annotations', 'quotas', 'shares', 'admin'].map(api => 
  `- ${api}: ${results.passed.find(r => r.key === `permissionConfig.apiPermissions.${api}`) ? '✅' : '❌'}`
).join('\n')}

### 8. Table Headers (5 headers)
- Permission column: ${results.passed.find(r => r.key === 'permissionConfig.table.permission') ? '✅' : '❌'}
- API endpoint column: ${results.passed.find(r => r.key === 'permissionConfig.apiTable.endpoint') ? '✅' : '❌'}
- API description column: ${results.passed.find(r => r.key === 'permissionConfig.apiTable.description') ? '✅' : '❌'}
- API methods column: ${results.passed.find(r => r.key === 'permissionConfig.apiTable.methods') ? '✅' : '❌'}
- API roles column: ${results.passed.find(r => r.key === 'permissionConfig.apiTable.roles') ? '✅' : '❌'}

### 9. Tab Labels (3 tabs)
- Matrix tab: ${results.passed.find(r => r.key === 'permissionConfig.tabs.matrix') ? '✅' : '❌'}
- API tab: ${results.passed.find(r => r.key === 'permissionConfig.tabs.api') ? '✅' : '❌'}
- Roles tab: ${results.passed.find(r => r.key === 'permissionConfig.tabs.roles') ? '✅' : '❌'}

### 10. Alert Messages
- Alert title: ${results.passed.find(r => r.key === 'permissionConfig.alert.title') ? '✅' : '❌'}
- Alert description: ${results.passed.find(r => r.key === 'permissionConfig.alert.description') ? '✅' : '❌'}

### 11. Buttons (2 buttons)
- Reset button: ${results.passed.find(r => r.key === 'permissionConfig.buttons.reset') ? '✅' : '❌'}
- Save button: ${results.passed.find(r => r.key === 'permissionConfig.buttons.save') ? '✅' : '❌'}

### 12. Placeholders
- Select tenant: ${results.passed.find(r => r.key === 'permissionConfig.placeholders.selectTenant') ? '✅' : '❌'}

### 13. Messages (3 messages)
- Save success: ${results.passed.find(r => r.key === 'permissionConfig.saveSuccess') ? '✅' : '❌'}
- Reset success: ${results.passed.find(r => r.key === 'permissionConfig.resetSuccess') ? '✅' : '❌'}
- Owner immutable: ${results.passed.find(r => r.key === 'permissionConfig.ownerPermissionImmutable') ? '✅' : '❌'}

### 14. Stats
- Permission count: ${results.passed.find(r => r.key === 'permissionConfig.stats.permissionCount') ? '✅' : '❌'}

## Detailed Results

### Passed Tests (${results.passed.length})

${results.passed.map(item => `- ✅ **${item.description}**
  - Key: \`${item.key}\`
  - Value: "${item.value}"`).join('\n\n')}

${results.failed.length > 0 ? `### Failed Tests (${results.failed.length})

${results.failed.map(item => `- ❌ **${item.description}**
  - Key: \`${item.key}\`
  - Error: ${item.error}`).join('\n\n')}` : ''}

${results.warnings.length > 0 ? `### Warnings (${results.warnings.length})

${results.warnings.map(item => `- ⚠️  **${item.description}**
  - Key: \`${item.key}\`
  - Warning: ${item.warning}`).join('\n\n')}` : ''}

## Requirements Validation

### Requirement 6.2: All translations display correctly
${results.failed.length === 0 ? '✅ **PASSED** - All translation keys are present and have valid values' : `❌ **FAILED** - ${results.failed.length} translation keys are missing or invalid`}

### Requirement 6.3: Browser console clean (no i18n warnings)
${results.failed.length === 0 ? '✅ **PASSED** - No missing translation keys that would cause console warnings' : `⚠️  **WARNING** - Missing keys may cause console warnings in browser`}

## Conclusion

${results.failed.length === 0 ? 
  '✅ **All tests passed!** The Permission Config page has complete translation coverage.' : 
  `❌ **Tests failed.** ${results.failed.length} translation keys need to be added or fixed.`}

## Next Steps

${results.failed.length === 0 ? 
  '- Proceed to manual browser testing to verify visual display\n- Check browser console for any runtime i18n warnings\n- Test language switching functionality' : 
  '- Add missing translation keys to frontend/src/locales/zh/admin.json\n- Re-run this test to verify fixes\n- Update English translations in frontend/src/locales/en/admin.json'}
`;

fs.writeFileSync(reportPath, report);
console.log(`\n📄 Detailed report saved to: ${reportPath}`);

// Exit with appropriate code
process.exit(results.failed.length > 0 ? 1 : 0);
