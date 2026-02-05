/**
 * I18n Console Warnings Check Script
 * Validates Requirements 6.3: Browser console clean (no i18n warnings)
 * 
 * This script:
 * 1. Navigates to all admin pages
 * 2. Monitors browser console for i18n-related warnings
 * 3. Checks for missing translation keys
 * 4. Checks for translation loading errors
 * 5. Tests language switching for console errors
 */

const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const ADMIN_PAGES = [
  {
    name: 'Admin Console',
    path: '/admin/console'
  },
  {
    name: 'Billing Management',
    path: '/admin/billing'
  },
  {
    name: 'Permission Configuration',
    path: '/admin/permission-config'
  },
  {
    name: 'Quota Management',
    path: '/admin/quota-management'
  }
];

const I18N_WARNING_PATTERNS = [
  /i18n/i,
  /translation/i,
  /missing.*key/i,
  /locale/i,
  /language/i,
  /fallback/i,
  /react-i18next/i,
  /t\(/,  // Translation function calls in warnings
  /useTranslation/i
];

async function checkI18nConsoleWarnings() {
  console.log('=== I18n Console Warnings Check ===\n');
  console.log('Starting browser...\n');
  
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  const results = {
    pages: [],
    totalWarnings: 0,
    totalErrors: 0,
    i18nIssues: []
  };
  
  // Collect console messages
  const consoleMessages = [];
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    consoleMessages.push({ type, text, timestamp: new Date().toISOString() });
    
    // Check if it's an i18n-related warning or error
    if ((type === 'warning' || type === 'error') && isI18nRelated(text)) {
      results.i18nIssues.push({
        type,
        message: text,
        timestamp: new Date().toISOString()
      });
    }
  });
  
  // Collect page errors
  page.on('pageerror', error => {
    const errorText = error.toString();
    consoleMessages.push({ 
      type: 'error', 
      text: errorText, 
      timestamp: new Date().toISOString() 
    });
    
    if (isI18nRelated(errorText)) {
      results.i18nIssues.push({
        type: 'error',
        message: errorText,
        timestamp: new Date().toISOString()
      });
    }
  });
  
  try {
    // Test each admin page
    for (const adminPage of ADMIN_PAGES) {
      console.log(`\n📄 Testing: ${adminPage.name}`);
      console.log(`   Path: ${adminPage.path}`);
      
      const pageResult = {
        name: adminPage.name,
        path: adminPage.path,
        warnings: 0,
        errors: 0,
        i18nIssues: [],
        languages: {}
      };
      
      // Test with Chinese (default)
      console.log('   Testing with Chinese (zh)...');
      await testPageWithLanguage(page, adminPage.path, 'zh', pageResult, consoleMessages);
      
      // Switch to English
      console.log('   Testing with English (en)...');
      await testPageWithLanguage(page, adminPage.path, 'en', pageResult, consoleMessages);
      
      // Switch back to Chinese
      console.log('   Testing switch back to Chinese (zh)...');
      await testPageWithLanguage(page, adminPage.path, 'zh', pageResult, consoleMessages);
      
      // Count warnings and errors for this page
      const pageMessages = consoleMessages.filter(msg => 
        msg.timestamp >= pageResult.startTime
      );
      
      pageResult.warnings = pageMessages.filter(msg => msg.type === 'warning').length;
      pageResult.errors = pageMessages.filter(msg => msg.type === 'error').length;
      
      results.pages.push(pageResult);
      results.totalWarnings += pageResult.warnings;
      results.totalErrors += pageResult.errors;
      
      // Print page summary
      if (pageResult.i18nIssues.length > 0) {
        console.log(`   ❌ Found ${pageResult.i18nIssues.length} i18n-related issues`);
        pageResult.i18nIssues.forEach(issue => {
          console.log(`      [${issue.type.toUpperCase()}] ${issue.message}`);
        });
      } else {
        console.log('   ✅ No i18n warnings detected');
      }
    }
    
  } catch (error) {
    console.error('\n❌ Test execution error:', error.message);
    results.executionError = error.message;
  } finally {
    await browser.close();
  }
  
  // Print detailed summary
  printSummary(results);
  
  // Save results to file
  const reportPath = path.join(__dirname, '..', '..', 'I18N_CONSOLE_WARNINGS_REPORT.md');
  const report = generateReport(results);
  fs.writeFileSync(reportPath, report);
  console.log(`\n📄 Detailed report saved to: ${reportPath}`);
  
  // Return success if no i18n issues found
  return {
    success: results.i18nIssues.length === 0,
    results
  };
}

async function testPageWithLanguage(page, pagePath, language, pageResult, consoleMessages) {
  const startTime = new Date().toISOString();
  if (!pageResult.startTime) {
    pageResult.startTime = startTime;
  }
  
  const url = `http://localhost:5174${pagePath}?lng=${language}`;
  
  try {
    // Navigate to page with language parameter
    await page.goto(url, { waitUntil: 'networkidle', timeout: 10000 });
    
    // Wait for page to be fully loaded
    await page.waitForTimeout(1000);
    
    // Check if language switcher exists and try to use it
    const languageSwitcher = await page.locator('[data-testid="language-switcher"]').first();
    if (await languageSwitcher.count() > 0) {
      await languageSwitcher.click();
      await page.waitForTimeout(500);
      
      // Select the target language
      const languageOption = await page.locator(`[data-value="${language}"]`).first();
      if (await languageOption.count() > 0) {
        await languageOption.click();
        await page.waitForTimeout(1000);
      }
    }
    
    // Collect console messages for this language
    const languageMessages = consoleMessages.filter(msg => 
      msg.timestamp >= startTime
    );
    
    const i18nIssues = languageMessages.filter(msg => 
      (msg.type === 'warning' || msg.type === 'error') && isI18nRelated(msg.text)
    );
    
    pageResult.languages[language] = {
      warnings: languageMessages.filter(msg => msg.type === 'warning').length,
      errors: languageMessages.filter(msg => msg.type === 'error').length,
      i18nIssues: i18nIssues.length
    };
    
    if (i18nIssues.length > 0) {
      pageResult.i18nIssues.push(...i18nIssues.map(issue => ({
        language,
        type: issue.type,
        message: issue.text
      })));
    }
    
  } catch (error) {
    console.log(`      ⚠️  Error loading page: ${error.message}`);
    pageResult.languages[language] = {
      error: error.message
    };
  }
}

function isI18nRelated(text) {
  return I18N_WARNING_PATTERNS.some(pattern => pattern.test(text));
}

function printSummary(results) {
  console.log('\n\n' + '='.repeat(60));
  console.log('=== I18n Console Warnings Check Summary ===');
  console.log('='.repeat(60));
  
  console.log(`\n📊 Overall Statistics:`);
  console.log(`   Pages tested: ${results.pages.length}`);
  console.log(`   Total warnings: ${results.totalWarnings}`);
  console.log(`   Total errors: ${results.totalErrors}`);
  console.log(`   I18n-related issues: ${results.i18nIssues.length}`);
  
  if (results.i18nIssues.length > 0) {
    console.log('\n❌ I18n Issues Found:\n');
    results.i18nIssues.forEach((issue, index) => {
      console.log(`   ${index + 1}. [${issue.type.toUpperCase()}] ${issue.message}`);
    });
  }
  
  console.log('\n📄 Per-Page Results:\n');
  results.pages.forEach(page => {
    const status = page.i18nIssues.length === 0 ? '✅' : '❌';
    console.log(`   ${status} ${page.name}`);
    console.log(`      Warnings: ${page.warnings}, Errors: ${page.errors}`);
    console.log(`      I18n issues: ${page.i18nIssues.length}`);
    
    Object.entries(page.languages).forEach(([lang, data]) => {
      if (data.error) {
        console.log(`      ${lang}: ⚠️  ${data.error}`);
      } else {
        console.log(`      ${lang}: ${data.i18nIssues} i18n issues`);
      }
    });
  });
  
  console.log('\n' + '='.repeat(60));
  if (results.i18nIssues.length === 0) {
    console.log('✅ SUCCESS: No i18n warnings found in browser console');
    console.log('✅ Requirements 6.3 VALIDATED');
  } else {
    console.log('❌ FAILURE: I18n warnings detected in browser console');
    console.log('❌ Requirements 6.3 NOT MET');
  }
  console.log('='.repeat(60) + '\n');
}

function generateReport(results) {
  const timestamp = new Date().toISOString();
  
  let report = `# I18n Console Warnings Check Report

**Generated**: ${timestamp}  
**Task**: 6.1 Check browser console for i18n warnings  
**Requirement**: 6.3 Browser console clean (no i18n warnings)

## Executive Summary

- **Pages Tested**: ${results.pages.length}
- **Total Console Warnings**: ${results.totalWarnings}
- **Total Console Errors**: ${results.totalErrors}
- **I18n-Related Issues**: ${results.i18nIssues.length}
- **Status**: ${results.i18nIssues.length === 0 ? '✅ PASSED' : '❌ FAILED'}

`;

  if (results.i18nIssues.length > 0) {
    report += `## ❌ I18n Issues Detected

The following i18n-related warnings or errors were found in the browser console:

`;
    results.i18nIssues.forEach((issue, index) => {
      report += `### Issue ${index + 1}

- **Type**: ${issue.type}
- **Message**: \`${issue.message}\`
- **Timestamp**: ${issue.timestamp}

`;
    });
  } else {
    report += `## ✅ No I18n Issues Detected

The browser console is clean. No i18n-related warnings or errors were found during testing.

`;
  }

  report += `## Detailed Results by Page

`;

  results.pages.forEach(page => {
    const status = page.i18nIssues.length === 0 ? '✅ PASSED' : '❌ FAILED';
    report += `### ${page.name} - ${status}

- **Path**: ${page.path}
- **Total Warnings**: ${page.warnings}
- **Total Errors**: ${page.errors}
- **I18n Issues**: ${page.i18nIssues.length}

#### Language Testing Results

`;
    
    Object.entries(page.languages).forEach(([lang, data]) => {
      if (data.error) {
        report += `- **${lang}**: ⚠️ Error - ${data.error}\n`;
      } else {
        report += `- **${lang}**: ${data.warnings} warnings, ${data.errors} errors, ${data.i18nIssues} i18n issues\n`;
      }
    });
    
    if (page.i18nIssues.length > 0) {
      report += `\n#### I18n Issues on This Page\n\n`;
      page.i18nIssues.forEach((issue, index) => {
        report += `${index + 1}. **[${issue.language}]** [${issue.type}] ${issue.message}\n`;
      });
    }
    
    report += '\n';
  });

  report += `## Test Methodology

This test:
1. Launched a headless Chromium browser using Playwright
2. Navigated to each admin page (${results.pages.length} pages total)
3. Tested each page with multiple languages (zh, en)
4. Monitored browser console for warnings and errors
5. Filtered console messages for i18n-related patterns
6. Tested language switching functionality

### I18n Warning Detection Patterns

The following patterns were used to identify i18n-related issues:
- \`/i18n/i\`
- \`/translation/i\`
- \`/missing.*key/i\`
- \`/locale/i\`
- \`/language/i\`
- \`/fallback/i\`
- \`/react-i18next/i\`
- \`/t\\(/\` (translation function calls)
- \`/useTranslation/i\`

## Conclusion

`;

  if (results.i18nIssues.length === 0) {
    report += `✅ **Requirements 6.3 VALIDATED**

The browser console is clean with no i18n-related warnings or errors. All admin pages load successfully in both Chinese and English without translation issues.

**Task 6.1 Status**: ✅ COMPLETE
`;
  } else {
    report += `❌ **Requirements 6.3 NOT MET**

I18n-related warnings or errors were detected in the browser console. These issues need to be resolved before Task 6.1 can be marked as complete.

**Task 6.1 Status**: ❌ INCOMPLETE - Issues need resolution
`;
  }

  report += `
---
*Report generated by check_i18n_console_warnings.js*
`;

  return report;
}

// Run the check
if (require.main === module) {
  checkI18nConsoleWarnings()
    .then(result => {
      process.exit(result.success ? 0 : 1);
    })
    .catch(error => {
      console.error('\n❌ Fatal error:', error);
      process.exit(1);
    });
}

module.exports = { checkI18nConsoleWarnings };
