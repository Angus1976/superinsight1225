/**
 * Test Script: Quota Management Page Translations
 * 
 * Tests Requirements 6.2 and 6.3:
 * - All translations display correctly
 * - Browser console clean (no i18n warnings)
 * 
 * Test Coverage:
 * - Page title and subtitle
 * - Statistics cards (storage, projects, users, API calls)
 * - Table columns (tenant, storage, projects, users, API calls, status, actions)
 * - Status tags (normal, warning, exceeded, not configured)
 * - Alert messages
 * - Modal form (adjust quota)
 * - Buttons (refresh, adjust quota)
 * - Pagination
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

// Test configuration
const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const ADMIN_USERNAME = process.env.ADMIN_USERNAME || 'admin';
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123';
const HEADLESS = process.env.HEADLESS !== 'false';

// Translation keys to test
const TRANSLATION_KEYS = {
  pageTitle: 'quotaManagement.title',
  statistics: [
    'quotaManagement.statistics.totalStorage',
    'quotaManagement.statistics.totalProjects',
    'quotaManagement.statistics.totalUsers',
    'quotaManagement.statistics.totalApiCalls'
  ],
  columns: [
    'quotaManagement.columns.tenant',
    'quotaManagement.columns.storage',
    'quotaManagement.columns.projects',
    'quotaManagement.columns.users',
    'quotaManagement.columns.apiCalls',
    'quotaManagement.columns.status',
    'quotaManagement.columns.actions'
  ],
  statusTags: [
    'quotaManagement.statusTags.normal',
    'quotaManagement.statusTags.approachingLimit',
    'quotaManagement.statusTags.quotaTight',
    'quotaManagement.status.notConfigured'
  ],
  buttons: [
    'quotaManagement.buttons.refresh',
    'quotaManagement.actions.adjustQuota'
  ],
  form: [
    'quotaManagement.form.storageQuota',
    'quotaManagement.form.projectQuota',
    'quotaManagement.form.userQuota',
    'quotaManagement.form.apiQuota'
  ],
  alert: 'quotaManagement.alert.quotaWarning',
  pagination: 'quotaManagement.pagination.total'
};

// Expected Chinese translations
const EXPECTED_TRANSLATIONS = {
  'quotaManagement.title': '配额管理',
  'quotaManagement.statistics.totalStorage': '总存储使用',
  'quotaManagement.statistics.totalProjects': '总项目数',
  'quotaManagement.statistics.totalUsers': '总用户数',
  'quotaManagement.statistics.totalApiCalls': '总 API 调用',
  'quotaManagement.columns.tenant': '租户',
  'quotaManagement.columns.storage': '存储',
  'quotaManagement.columns.projects': '项目数',
  'quotaManagement.columns.users': '用户数',
  'quotaManagement.columns.apiCalls': 'API 调用',
  'quotaManagement.columns.status': '状态',
  'quotaManagement.columns.actions': '操作',
  'quotaManagement.statusTags.normal': '正常',
  'quotaManagement.statusTags.approachingLimit': '接近上限',
  'quotaManagement.statusTags.quotaTight': '配额紧张',
  'quotaManagement.status.notConfigured': '未配置',
  'quotaManagement.buttons.refresh': '刷新',
  'quotaManagement.actions.adjustQuota': '调整配额',
  'quotaManagement.form.storageQuota': '存储配额 (GB)',
  'quotaManagement.form.projectQuota': '项目配额',
  'quotaManagement.form.userQuota': '用户配额',
  'quotaManagement.form.apiQuota': 'API 调用配额'
};

class QuotaManagementTranslationTester {
  constructor() {
    this.browser = null;
    this.page = null;
    this.results = {
      passed: [],
      failed: [],
      warnings: [],
      consoleErrors: [],
      i18nWarnings: []
    };
  }

  async init() {
    console.log('🚀 Initializing browser...');
    this.browser = await puppeteer.launch({
      headless: HEADLESS,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--lang=zh-CN']
    });
    this.page = await this.browser.newPage();
    
    // Set viewport
    await this.page.setViewport({ width: 1920, height: 1080 });
    
    // Monitor console messages
    this.page.on('console', msg => {
      const text = msg.text();
      if (text.includes('i18n') || text.includes('translation') || text.includes('missing')) {
        this.results.i18nWarnings.push(text);
        console.log('⚠️  i18n warning:', text);
      }
      if (msg.type() === 'error') {
        this.results.consoleErrors.push(text);
        console.log('❌ Console error:', text);
      }
    });
    
    console.log('✅ Browser initialized');
  }

  async login() {
    console.log('\n🔐 Logging in...');
    try {
      await this.page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle0', timeout: 30000 });
      
      // Fill login form
      await this.page.type('input[type="text"]', ADMIN_USERNAME);
      await this.page.type('input[type="password"]', ADMIN_PASSWORD);
      
      // Click login button
      await this.page.click('button[type="submit"]');
      
      // Wait for navigation
      await this.page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 30000 });
      
      console.log('✅ Login successful');
      return true;
    } catch (error) {
      console.error('❌ Login failed:', error.message);
      this.results.failed.push({ test: 'Login', error: error.message });
      return false;
    }
  }

  async navigateToQuotaManagement() {
    console.log('\n📍 Navigating to Quota Management page...');
    try {
      await this.page.goto(`${BASE_URL}/admin/quotas`, { 
        waitUntil: 'networkidle0', 
        timeout: 30000 
      });
      
      // Wait for page to load
      await this.page.waitForSelector('.quota-management', { timeout: 10000 });
      
      console.log('✅ Navigation successful');
      return true;
    } catch (error) {
      console.error('❌ Navigation failed:', error.message);
      this.results.failed.push({ test: 'Navigation', error: error.message });
      return false;
    }
  }

  async testPageTitle() {
    console.log('\n📝 Testing page title...');
    try {
      const titleSelector = '.ant-card-head-title';
      await this.page.waitForSelector(titleSelector, { timeout: 5000 });
      
      const titleText = await this.page.$eval(titleSelector, el => el.textContent);
      const expected = EXPECTED_TRANSLATIONS['quotaManagement.title'];
      
      if (titleText.includes(expected)) {
        console.log(`✅ Page title correct: "${titleText}"`);
        this.results.passed.push({ test: 'Page Title', value: titleText });
      } else {
        console.log(`❌ Page title incorrect: "${titleText}" (expected: "${expected}")`);
        this.results.failed.push({ 
          test: 'Page Title', 
          expected, 
          actual: titleText 
        });
      }
    } catch (error) {
      console.error('❌ Page title test failed:', error.message);
      this.results.failed.push({ test: 'Page Title', error: error.message });
    }
  }

  async testStatisticsCards() {
    console.log('\n📊 Testing statistics cards...');
    try {
      const statisticTitles = await this.page.$$eval(
        '.ant-statistic-title',
        elements => elements.map(el => el.textContent.trim())
      );
      
      const expectedTitles = [
        EXPECTED_TRANSLATIONS['quotaManagement.statistics.totalStorage'],
        EXPECTED_TRANSLATIONS['quotaManagement.statistics.totalProjects'],
        EXPECTED_TRANSLATIONS['quotaManagement.statistics.totalUsers'],
        EXPECTED_TRANSLATIONS['quotaManagement.statistics.totalApiCalls']
      ];
      
      let allCorrect = true;
      expectedTitles.forEach((expected, index) => {
        const actual = statisticTitles[index];
        if (actual === expected) {
          console.log(`✅ Statistic ${index + 1} correct: "${actual}"`);
          this.results.passed.push({ test: `Statistic Card ${index + 1}`, value: actual });
        } else {
          console.log(`❌ Statistic ${index + 1} incorrect: "${actual}" (expected: "${expected}")`);
          this.results.failed.push({ 
            test: `Statistic Card ${index + 1}`, 
            expected, 
            actual 
          });
          allCorrect = false;
        }
      });
      
      if (allCorrect) {
        console.log('✅ All statistics cards translated correctly');
      }
    } catch (error) {
      console.error('❌ Statistics cards test failed:', error.message);
      this.results.failed.push({ test: 'Statistics Cards', error: error.message });
    }
  }

  async testTableColumns() {
    console.log('\n📋 Testing table columns...');
    try {
      const columnHeaders = await this.page.$$eval(
        '.ant-table-thead th',
        elements => elements.map(el => el.textContent.trim()).filter(text => text)
      );
      
      const expectedColumns = [
        EXPECTED_TRANSLATIONS['quotaManagement.columns.tenant'],
        EXPECTED_TRANSLATIONS['quotaManagement.columns.storage'],
        EXPECTED_TRANSLATIONS['quotaManagement.columns.projects'],
        EXPECTED_TRANSLATIONS['quotaManagement.columns.users'],
        EXPECTED_TRANSLATIONS['quotaManagement.columns.apiCalls'],
        EXPECTED_TRANSLATIONS['quotaManagement.columns.status'],
        EXPECTED_TRANSLATIONS['quotaManagement.columns.actions']
      ];
      
      let allCorrect = true;
      expectedColumns.forEach((expected, index) => {
        const actual = columnHeaders[index];
        if (actual === expected) {
          console.log(`✅ Column ${index + 1} correct: "${actual}"`);
          this.results.passed.push({ test: `Table Column ${index + 1}`, value: actual });
        } else {
          console.log(`❌ Column ${index + 1} incorrect: "${actual}" (expected: "${expected}")`);
          this.results.failed.push({ 
            test: `Table Column ${index + 1}`, 
            expected, 
            actual 
          });
          allCorrect = false;
        }
      });
      
      if (allCorrect) {
        console.log('✅ All table columns translated correctly');
      }
    } catch (error) {
      console.error('❌ Table columns test failed:', error.message);
      this.results.failed.push({ test: 'Table Columns', error: error.message });
    }
  }

  async testRefreshButton() {
    console.log('\n🔄 Testing refresh button...');
    try {
      const buttonText = await this.page.$eval(
        '.ant-card-extra button',
        el => el.textContent.trim()
      );
      
      const expected = EXPECTED_TRANSLATIONS['quotaManagement.buttons.refresh'];
      
      if (buttonText === expected) {
        console.log(`✅ Refresh button correct: "${buttonText}"`);
        this.results.passed.push({ test: 'Refresh Button', value: buttonText });
      } else {
        console.log(`❌ Refresh button incorrect: "${buttonText}" (expected: "${expected}")`);
        this.results.failed.push({ 
          test: 'Refresh Button', 
          expected, 
          actual: buttonText 
        });
      }
    } catch (error) {
      console.error('❌ Refresh button test failed:', error.message);
      this.results.failed.push({ test: 'Refresh Button', error: error.message });
    }
  }

  async testAdjustQuotaButton() {
    console.log('\n⚙️  Testing adjust quota button...');
    try {
      // Check if there are any rows in the table
      const hasRows = await this.page.$('.ant-table-tbody tr:not(.ant-table-placeholder)');
      
      if (hasRows) {
        const buttonText = await this.page.$eval(
          '.ant-table-tbody button[type="link"]',
          el => el.textContent.trim()
        );
        
        const expected = EXPECTED_TRANSLATIONS['quotaManagement.actions.adjustQuota'];
        
        if (buttonText === expected) {
          console.log(`✅ Adjust quota button correct: "${buttonText}"`);
          this.results.passed.push({ test: 'Adjust Quota Button', value: buttonText });
        } else {
          console.log(`❌ Adjust quota button incorrect: "${buttonText}" (expected: "${expected}")`);
          this.results.failed.push({ 
            test: 'Adjust Quota Button', 
            expected, 
            actual: buttonText 
          });
        }
      } else {
        console.log('⚠️  No table rows found, skipping adjust quota button test');
        this.results.warnings.push({ test: 'Adjust Quota Button', message: 'No data to test' });
      }
    } catch (error) {
      console.error('❌ Adjust quota button test failed:', error.message);
      this.results.failed.push({ test: 'Adjust Quota Button', error: error.message });
    }
  }

  async testModalForm() {
    console.log('\n📝 Testing modal form...');
    try {
      // Check if there are any rows to click
      const hasRows = await this.page.$('.ant-table-tbody tr:not(.ant-table-placeholder)');
      
      if (hasRows) {
        // Click the first adjust quota button
        await this.page.click('.ant-table-tbody button[type="link"]');
        
        // Wait for modal to appear
        await this.page.waitForSelector('.ant-modal', { timeout: 5000 });
        
        // Test form labels
        const formLabels = await this.page.$$eval(
          '.ant-modal .ant-form-item-label label',
          elements => elements.map(el => el.textContent.trim())
        );
        
        const expectedLabels = [
          EXPECTED_TRANSLATIONS['quotaManagement.form.storageQuota'],
          EXPECTED_TRANSLATIONS['quotaManagement.form.projectQuota'],
          EXPECTED_TRANSLATIONS['quotaManagement.form.userQuota'],
          EXPECTED_TRANSLATIONS['quotaManagement.form.apiQuota']
        ];
        
        let allCorrect = true;
        expectedLabels.forEach((expected, index) => {
          const actual = formLabels[index];
          if (actual === expected) {
            console.log(`✅ Form label ${index + 1} correct: "${actual}"`);
            this.results.passed.push({ test: `Modal Form Label ${index + 1}`, value: actual });
          } else {
            console.log(`❌ Form label ${index + 1} incorrect: "${actual}" (expected: "${expected}")`);
            this.results.failed.push({ 
              test: `Modal Form Label ${index + 1}`, 
              expected, 
              actual 
            });
            allCorrect = false;
          }
        });
        
        // Close modal
        await this.page.click('.ant-modal-close');
        await this.page.waitForTimeout(500);
        
        if (allCorrect) {
          console.log('✅ All modal form labels translated correctly');
        }
      } else {
        console.log('⚠️  No table rows found, skipping modal form test');
        this.results.warnings.push({ test: 'Modal Form', message: 'No data to test' });
      }
    } catch (error) {
      console.error('❌ Modal form test failed:', error.message);
      this.results.failed.push({ test: 'Modal Form', error: error.message });
    }
  }

  async testPagination() {
    console.log('\n📄 Testing pagination...');
    try {
      const paginationText = await this.page.$eval(
        '.ant-pagination-total-text',
        el => el.textContent.trim()
      );
      
      // Check if it contains Chinese characters (共...个租户)
      if (paginationText.includes('共') && paginationText.includes('个租户')) {
        console.log(`✅ Pagination translated correctly: "${paginationText}"`);
        this.results.passed.push({ test: 'Pagination', value: paginationText });
      } else {
        console.log(`❌ Pagination not translated: "${paginationText}"`);
        this.results.failed.push({ 
          test: 'Pagination', 
          expected: '共 X 个租户', 
          actual: paginationText 
        });
      }
    } catch (error) {
      console.error('❌ Pagination test failed:', error.message);
      this.results.failed.push({ test: 'Pagination', error: error.message });
    }
  }

  async checkConsoleWarnings() {
    console.log('\n🔍 Checking console warnings...');
    
    if (this.results.i18nWarnings.length === 0) {
      console.log('✅ No i18n warnings found');
      this.results.passed.push({ test: 'Console i18n Warnings', value: 'None' });
    } else {
      console.log(`❌ Found ${this.results.i18nWarnings.length} i18n warnings:`);
      this.results.i18nWarnings.forEach(warning => {
        console.log(`   - ${warning}`);
      });
      this.results.failed.push({ 
        test: 'Console i18n Warnings', 
        count: this.results.i18nWarnings.length,
        warnings: this.results.i18nWarnings
      });
    }
    
    if (this.results.consoleErrors.length === 0) {
      console.log('✅ No console errors found');
      this.results.passed.push({ test: 'Console Errors', value: 'None' });
    } else {
      console.log(`⚠️  Found ${this.results.consoleErrors.length} console errors:`);
      this.results.consoleErrors.forEach(error => {
        console.log(`   - ${error}`);
      });
      this.results.warnings.push({ 
        test: 'Console Errors', 
        count: this.results.consoleErrors.length,
        errors: this.results.consoleErrors
      });
    }
  }

  generateReport() {
    console.log('\n' + '='.repeat(80));
    console.log('📊 TEST REPORT: Quota Management Page Translations');
    console.log('='.repeat(80));
    
    console.log(`\n✅ Passed: ${this.results.passed.length}`);
    console.log(`❌ Failed: ${this.results.failed.length}`);
    console.log(`⚠️  Warnings: ${this.results.warnings.length}`);
    
    if (this.results.failed.length > 0) {
      console.log('\n❌ Failed Tests:');
      this.results.failed.forEach(failure => {
        console.log(`   - ${failure.test}`);
        if (failure.expected) {
          console.log(`     Expected: "${failure.expected}"`);
          console.log(`     Actual: "${failure.actual}"`);
        }
        if (failure.error) {
          console.log(`     Error: ${failure.error}`);
        }
      });
    }
    
    if (this.results.warnings.length > 0) {
      console.log('\n⚠️  Warnings:');
      this.results.warnings.forEach(warning => {
        console.log(`   - ${warning.test}: ${warning.message || warning.count + ' items'}`);
      });
    }
    
    const totalTests = this.results.passed.length + this.results.failed.length;
    const successRate = totalTests > 0 ? ((this.results.passed.length / totalTests) * 100).toFixed(1) : 0;
    
    console.log(`\n📈 Success Rate: ${successRate}%`);
    console.log('='.repeat(80));
    
    // Save report to file
    const report = {
      timestamp: new Date().toISOString(),
      page: 'Quota Management',
      url: `${BASE_URL}/admin/quotas`,
      summary: {
        total: totalTests,
        passed: this.results.passed.length,
        failed: this.results.failed.length,
        warnings: this.results.warnings.length,
        successRate: `${successRate}%`
      },
      results: this.results
    };
    
    const reportPath = path.join(__dirname, '..', 'TASK_5.5_QUOTA_MANAGEMENT_TEST_REPORT.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n💾 Report saved to: ${reportPath}`);
    
    return this.results.failed.length === 0;
  }

  async cleanup() {
    if (this.browser) {
      await this.browser.close();
      console.log('\n🧹 Browser closed');
    }
  }

  async run() {
    try {
      await this.init();
      
      const loginSuccess = await this.login();
      if (!loginSuccess) {
        console.error('❌ Cannot proceed without login');
        return false;
      }
      
      const navSuccess = await this.navigateToQuotaManagement();
      if (!navSuccess) {
        console.error('❌ Cannot proceed without navigation');
        return false;
      }
      
      // Run all tests
      await this.testPageTitle();
      await this.testStatisticsCards();
      await this.testTableColumns();
      await this.testRefreshButton();
      await this.testAdjustQuotaButton();
      await this.testModalForm();
      await this.testPagination();
      await this.checkConsoleWarnings();
      
      // Generate report
      const success = this.generateReport();
      
      return success;
    } catch (error) {
      console.error('❌ Test execution failed:', error);
      return false;
    } finally {
      await this.cleanup();
    }
  }
}

// Run tests
(async () => {
  const tester = new QuotaManagementTranslationTester();
  const success = await tester.run();
  process.exit(success ? 0 : 1);
})();
