#!/usr/bin/env python3
"""
Frontend Login Test Script
Tests the frontend login functionality and verifies that all pages load correctly.
"""

import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configuration
FRONTEND_URL = "http://localhost:5173"
TEST_USER = {
    "username": "admin_user",
    "password": "Admin@123456",
    "role": "admin"
}

class FrontendLoginTester:
    def __init__(self):
        # Setup Chrome options for headless testing
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
        except Exception as e:
            print(f"❌ Failed to initialize Chrome driver: {e}")
            print("💡 Please install ChromeDriver or use manual testing")
            self.driver = None
    
    def test_frontend_accessibility(self):
        """Test if frontend is accessible and serving React app."""
        try:
            response = requests.get(FRONTEND_URL, timeout=5)
            if response.status_code == 200:
                if "root" in response.text and "<!DOCTYPE html>" in response.text:
                    print("✅ Frontend is accessible and serving React app")
                    return True
                else:
                    print("❌ Frontend accessible but not serving React app")
                    return False
            else:
                print(f"❌ Frontend not accessible: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Frontend accessibility test failed: {e}")
            return False
    
    def test_login_functionality(self):
        """Test login functionality through the browser."""
        if not self.driver:
            print("⚠️  Skipping browser tests - Chrome driver not available")
            return False
        
        try:
            print("🌐 Opening frontend login page...")
            self.driver.get(f"{FRONTEND_URL}/login")
            
            # Wait for page to load
            time.sleep(2)
            
            # Check if login form is present
            try:
                username_field = self.wait.until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                password_field = self.driver.find_element(By.NAME, "password")
                login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                
                print("✅ Login form elements found")
                
                # Fill in credentials
                username_field.clear()
                username_field.send_keys(TEST_USER["username"])
                
                password_field.clear()
                password_field.send_keys(TEST_USER["password"])
                
                print(f"📝 Filled credentials for {TEST_USER['username']}")
                
                # Click login button
                login_button.click()
                
                # Wait for redirect or success
                time.sleep(3)
                
                # Check if we're redirected to dashboard or if login was successful
                current_url = self.driver.current_url
                
                if "/dashboard" in current_url or "/login" not in current_url:
                    print("✅ Login successful - redirected to dashboard")
                    return True
                else:
                    # Check for error messages
                    try:
                        error_element = self.driver.find_element(By.CSS_SELECTOR, ".ant-message-error, .error-message, .alert-error")
                        error_text = error_element.text
                        print(f"❌ Login failed with error: {error_text}")
                    except NoSuchElementException:
                        print("❌ Login failed - still on login page with no clear error")
                    return False
                    
            except TimeoutException:
                print("❌ Login form not found - page may not have loaded correctly")
                return False
                
        except Exception as e:
            print(f"❌ Login test failed: {e}")
            return False
    
    def test_dashboard_pages(self):
        """Test navigation to different dashboard pages."""
        if not self.driver:
            print("⚠️  Skipping dashboard tests - Chrome driver not available")
            return {}
        
        pages_to_test = [
            ("/dashboard", "Dashboard"),
            ("/tasks", "Tasks"),
            ("/projects", "Projects"),
            ("/users", "Users"),
            ("/settings", "Settings"),
            ("/reports", "Reports"),
            ("/quality", "Quality")
        ]
        
        results = {}
        
        for path, name in pages_to_test:
            try:
                print(f"🔍 Testing {name} page ({path})...")
                self.driver.get(f"{FRONTEND_URL}{path}")
                time.sleep(2)
                
                # Check if page loaded without errors
                current_url = self.driver.current_url
                page_title = self.driver.title
                
                # Look for common error indicators
                error_indicators = [
                    "404", "Not Found", "Error", "Cannot GET",
                    "This page could not be found"
                ]
                
                page_source = self.driver.page_source.lower()
                has_error = any(indicator.lower() in page_source for indicator in error_indicators)
                
                if has_error:
                    print(f"❌ {name} page has errors")
                    results[path] = False
                else:
                    print(f"✅ {name} page loaded successfully")
                    results[path] = True
                    
            except Exception as e:
                print(f"❌ {name} page test failed: {e}")
                results[path] = False
        
        return results
    
    def run_comprehensive_test(self):
        """Run comprehensive frontend testing."""
        print("🚀 Starting Comprehensive Frontend Testing")
        print("=" * 50)
        
        results = {
            "frontend_accessible": False,
            "login_functional": False,
            "pages": {}
        }
        
        # Test 1: Frontend accessibility
        print("\n📡 Testing Frontend Accessibility...")
        results["frontend_accessible"] = self.test_frontend_accessibility()
        
        if not results["frontend_accessible"]:
            print("❌ Frontend not accessible - skipping other tests")
            return results
        
        # Test 2: Login functionality
        print("\n🔐 Testing Login Functionality...")
        results["login_functional"] = self.test_login_functionality()
        
        if results["login_functional"]:
            # Test 3: Dashboard pages
            print("\n📊 Testing Dashboard Pages...")
            results["pages"] = self.test_dashboard_pages()
        else:
            print("⚠️  Skipping page tests - login not functional")
        
        return results
    
    def generate_report(self, results):
        """Generate test report."""
        print("\n" + "=" * 50)
        print("📋 FRONTEND TESTING REPORT")
        print("=" * 50)
        
        # Frontend accessibility
        status = "✅ PASS" if results["frontend_accessible"] else "❌ FAIL"
        print(f"Frontend Accessible: {status}")
        
        # Login functionality
        status = "✅ PASS" if results["login_functional"] else "❌ FAIL"
        print(f"Login Functional: {status}")
        
        # Page tests
        if results["pages"]:
            print("\nPage Navigation Tests:")
            passed_pages = 0
            total_pages = len(results["pages"])
            
            for page, passed in results["pages"].items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"  {page}: {status}")
                if passed:
                    passed_pages += 1
            
            page_success_rate = (passed_pages / total_pages * 100) if total_pages > 0 else 0
            print(f"\nPage Success Rate: {page_success_rate:.1f}% ({passed_pages}/{total_pages})")
        
        # Overall assessment
        print("\n" + "=" * 50)
        print("🎯 OVERALL ASSESSMENT")
        print("=" * 50)
        
        if results["frontend_accessible"] and results["login_functional"]:
            if results["pages"]:
                page_success = sum(results["pages"].values()) / len(results["pages"])
                if page_success >= 0.8:
                    print("🎉 EXCELLENT: Frontend is fully functional!")
                elif page_success >= 0.6:
                    print("👍 GOOD: Frontend mostly functional with minor issues")
                else:
                    print("⚠️  FAIR: Frontend has navigation issues")
            else:
                print("👍 GOOD: Core functionality working")
        elif results["frontend_accessible"]:
            print("⚠️  PARTIAL: Frontend accessible but login issues")
        else:
            print("🚨 CRITICAL: Frontend not accessible")
        
        # Recommendations
        print("\n📝 RECOMMENDATIONS:")
        if not results["frontend_accessible"]:
            print("  - Check if frontend container is running")
            print("  - Verify frontend build and configuration")
        elif not results["login_functional"]:
            print("  - Check authentication API endpoints")
            print("  - Verify user credentials and database")
        elif results["pages"] and not all(results["pages"].values()):
            failed_pages = [page for page, passed in results["pages"].items() if not passed]
            print(f"  - Fix navigation issues for: {', '.join(failed_pages)}")
        else:
            print("  - System appears to be working well!")
    
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()

def main():
    """Main function."""
    tester = FrontendLoginTester()
    
    try:
        results = tester.run_comprehensive_test()
        tester.generate_report(results)
        
        # Save results
        with open("frontend_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: frontend_test_results.json")
        
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()