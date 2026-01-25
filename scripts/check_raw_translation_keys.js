/**
 * Check for Raw Translation Keys in Admin Console
 * 
 * This script navigates through all admin pages and checks for:
 * 1. Text that looks like translation keys (contains dots, camelCase)
 * 2. Text matching pattern: word.word.word
 * 3. Text with common translation key prefixes
 * 
 * Usage: node scripts/check_raw_translation_keys.js
 */

const puppeteer = require('puppeteer');

// Common translation key patterns
const TRANSLATION_KEY_PATTERNS = [
  /\w+\.\w+\.\w+/,  // Basic pattern: word.word.word
  /^[a-z]+[A-Z]/,   // camelCase starting with lowercase
  /billingManagement\./,
  /permissionConfig\./,
  /quotaManagement\./,
  /console\./,
  /admin\./,
  /common\./,
];

// Known valid text that might match patterns (false positives)
const WHITELIST = [
  'localhost:5173',
  'localhost:8000',
  'http://',
  'https://',
  'www.',
  '.com',
  '.json',
  '.ts',
  '.tsx',
  'v1.0',
  'v2.0',
  'API',
  'ID',
  'URL',
];

function looksLikeTranslationKey(text) {
  // Skip if in whitelist
  if (WHITELIST.some(w => text.includes(w))) {
    return false;
  }
  
  // Check if matches any translation key pattern
  return TRANSLATION_KEY_PATTERNS.some(pattern => pattern.test(text));
}

async function checkPageForRawKeys(page, pageName, url) {
  console.log(`\n📄 Checking ${pageName}...`);
  console.log(`   URL: ${url}`);
  
  try {
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 10000 });
    await page.waitForTimeout(2000); // Wait for dynamic content
    
    // Get all text content from the page
    const textContent = await page.evaluate(() => {
      const elements = document.querySelectorAll('body *');
      const texts = [];
      
      elements.forEach(el => {
        // Get direct text nodes only (not children)
        for (let node of el.childNodes) {
          if (node.nodeType === Node.TEXT_NODE) {
            const text = node.textContent.trim();
            if (text && text.length > 0) {
              texts.push({
                text: text,
                tag: el.tagName,
                className: el.className,
              });
            }
          }
        }
        
        // Also check placeholder and title attributes
        if (el.placeholder) {
          texts.push({
            text: el.placeholder,
            tag: el.tagName,
            className: el.className,
            attribute: 'placeholder',
          });
        }
        if (el.title) {
          texts.push({
            text: el.title,
            tag: el.tagName,
            className: el.className,
            attribute: 'title',
          });
        }
      });
      
      return texts;
    });
    
    // Check each text for translation key patterns
    const suspiciousTexts = [];
    textContent.forEach(item => {
      if (looksLikeTranslationKey(item.text)) {
        suspiciousTexts.push(item);
      }
    });
    
    if (suspiciousTexts.length === 0) {
      console.log(`   ✅ No raw translation keys found`);
      return { page: pageName, url, status: 'pass', issues: [] };
    } else {
      console.log(`   ❌ Found ${suspiciousTexts.length} suspicious text(s):`);
      suspiciousTexts.forEach((item, idx) => {
        const location = item.attribute 
          ? `${item.tag}.${item.attribute}` 
          : item.tag;
        console.log(`      ${idx + 1}. "${item.text}" (in ${location})`);
      });
      return { 
        page: pageName, 
        url, 
        status: 'fail', 
        issues: suspiciousTexts 
      };
    }
  } catch (error) {
    console.log(`   ⚠️  Error checking page: ${error.message}`);
    return { 
      page: pageName, 
      url, 
      status: 'error', 
      error: error.message 
    };
  }
}

async function checkAllPages() {
  console.log('🔍 Starting Raw Translation Key Check...\n');
  console.log('=' .repeat(60));
  
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  try {
    const page = await browser.newPage();
    
    // Set viewport
    await page.setViewport({ width: 1920, height: 1080 });
    
    // Enable console logging
    page.on('console', msg => {
      if (msg.type() === 'error' || msg.type() === 'warning') {
        console.log(`   [Browser ${msg.type()}]:`, msg.text());
      }
    });
    
    const baseUrl = 'http://localhost:5173';
    
    // Define all admin pages to check
    const pagesToCheck = [
      { name: 'Admin Console - Overview', url: `${baseUrl}/admin/console` },
      { name: 'Admin Console - Billing Management', url: `${baseUrl}/admin/billing` },
      { name: 'Admin Console - Permission Config', url: `${baseUrl}/admin/permissions` },
      { name: 'Admin Console - Quota Management', url: `${baseUrl}/admin/quota` },
      { name: 'Admin Console - Tenant Management', url: `${baseUrl}/admin/tenants` },
    ];
    
    const results = [];
    
    // Check each page in both languages
    for (const lang of ['zh', 'en']) {
      console.log(`\n${'='.repeat(60)}`);
      console.log(`🌐 Testing in ${lang === 'zh' ? 'Chinese' : 'English'} (${lang})`);
      console.log('='.repeat(60));
      
      // Switch language by setting localStorage
      await page.goto(baseUrl, { waitUntil: 'networkidle0' });
      await page.evaluate((language) => {
        localStorage.setItem('i18nextLng', language);
      }, lang);
      
      // Check each page
      for (const pageInfo of pagesToCheck) {
        const result = await checkPageForRawKeys(
          page, 
          `${pageInfo.name} (${lang})`, 
          pageInfo.url
        );
        results.push(result);
      }
    }
    
    // Summary
    console.log('\n' + '='.repeat(60));
    console.log('📊 SUMMARY');
    console.log('='.repeat(60));
    
    const passed = results.filter(r => r.status === 'pass').length;
    const failed = results.filter(r => r.status === 'fail').length;
    const errors = results.filter(r => r.status === 'error').length;
    
    console.log(`\nTotal pages checked: ${results.length}`);
    console.log(`✅ Passed: ${passed}`);
    console.log(`❌ Failed: ${failed}`);
    console.log(`⚠️  Errors: ${errors}`);
    
    if (failed > 0) {
      console.log('\n❌ FAILED PAGES:');
      results.filter(r => r.status === 'fail').forEach(r => {
        console.log(`\n   ${r.page}`);
        console.log(`   URL: ${r.url}`);
        console.log(`   Issues found: ${r.issues.length}`);
        r.issues.forEach((issue, idx) => {
          console.log(`      ${idx + 1}. "${issue.text}"`);
        });
      });
    }
    
    if (errors > 0) {
      console.log('\n⚠️  PAGES WITH ERRORS:');
      results.filter(r => r.status === 'error').forEach(r => {
        console.log(`   ${r.page}: ${r.error}`);
      });
    }
    
    console.log('\n' + '='.repeat(60));
    
    if (failed === 0 && errors === 0) {
      console.log('✅ ALL CHECKS PASSED - No raw translation keys found!');
      return 0;
    } else {
      console.log('❌ CHECKS FAILED - Raw translation keys or errors detected!');
      return 1;
    }
    
  } catch (error) {
    console.error('\n❌ Fatal error:', error);
    return 1;
  } finally {
    await browser.close();
  }
}

// Run the checks
checkAllPages()
  .then(exitCode => {
    process.exit(exitCode);
  })
  .catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
