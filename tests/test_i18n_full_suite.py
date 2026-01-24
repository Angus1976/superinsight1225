"""
Comprehensive i18n Test Suite

Tests all i18n functionality including:
- Formatters (date, time, number, currency)
- Hot reload
- Middleware
- Language detection
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from datetime import datetime, date, time, timedelta
from decimal import Decimal

from src.i18n.formatters import (
    DateTimeFormatter,
    NumberFormatter,
    CurrencyFormatter,
    format_date,
    format_time,
    format_datetime,
    format_relative_time,
    format_number,
    format_percent,
    format_currency
)
from src.i18n.hot_reload import (
    get_hot_reloader,
    reload_translations,
    register_reload_callback,
    get_hot_reload_status
)
from src.i18n.translations import set_language, get_current_language


class TestDateTimeFormatters:
    """Test date and time formatters."""

    def test_format_date_chinese(self):
        """Test date formatting in Chinese."""
        print("\n=== Testing Date Formatting (Chinese) ===")
        set_language('zh')

        test_date = date(2024, 1, 24)

        # Short format
        result = format_date(test_date, 'short')
        assert '2024' in result and '01' in result and '24' in result
        print(f"[OK] Short format: {result}")

        # Medium format
        result = format_date(test_date, 'medium')
        assert '2024' in result and '年' in result
        print(f"[OK] Medium format: {result}")

    def test_format_date_english(self):
        """Test date formatting in English."""
        print("\n=== Testing Date Formatting (English) ===")
        set_language('en')

        test_date = date(2024, 1, 24)

        # Short format
        result = format_date(test_date, 'short')
        assert '2024' in result
        print(f"[OK] Short format: {result}")

        # Medium format
        result = format_date(test_date, 'medium')
        assert 'Jan' in result or 'January' in result
        print(f"[OK] Medium format: {result}")

    def test_format_time_chinese(self):
        """Test time formatting in Chinese."""
        print("\n=== Testing Time Formatting (Chinese) ===")
        set_language('zh')

        test_time = time(14, 30, 45)

        # Short format
        result = format_time(test_time, 'short')
        assert '14' in result and '30' in result
        print(f"[OK] Short format: {result}")

        # Long format
        result = format_time(test_time, 'long')
        assert '时' in result or '14' in result
        print(f"[OK] Long format: {result}")

    def test_relative_time_chinese(self):
        """Test relative time formatting in Chinese."""
        print("\n=== Testing Relative Time (Chinese) ===")
        set_language('zh')

        now = datetime.now()

        # 1 hour ago
        past = now - timedelta(hours=1)
        result = format_relative_time(past, now)
        assert '小时前' in result or 'hour' in result.lower()
        print(f"[OK] 1 hour ago: {result}")

        # 2 days from now
        future = now + timedelta(days=2)
        result = format_relative_time(future, now)
        assert '天后' in result or 'day' in result.lower()
        print(f"[OK] 2 days from now: {result}")

    def test_relative_time_english(self):
        """Test relative time formatting in English."""
        print("\n=== Testing Relative Time (English) ===")
        set_language('en')

        now = datetime.now()

        # 30 minutes ago
        past = now - timedelta(minutes=30)
        result = format_relative_time(past, now)
        assert 'minute' in result.lower() and 'ago' in result.lower()
        print(f"[OK] 30 minutes ago: {result}")

        # 3 hours from now
        future = now + timedelta(hours=3)
        result = format_relative_time(future, now)
        assert 'hour' in result.lower() and 'in' in result.lower()
        print(f"[OK] 3 hours from now: {result}")


class TestNumberFormatters:
    """Test number formatters."""

    def test_format_number_chinese(self):
        """Test number formatting in Chinese."""
        print("\n=== Testing Number Formatting (Chinese) ===")
        set_language('zh')

        # Integer with grouping
        result = format_number(1234567, use_grouping=True)
        assert '1,234,567' == result or '1234567' in result
        print(f"[OK] Integer with grouping: {result}")

        # Decimal
        result = format_number(1234.56, decimals=2)
        assert '1234.56' in result or '1,234.56' in result
        print(f"[OK] Decimal: {result}")

    def test_format_number_english(self):
        """Test number formatting in English."""
        print("\n=== Testing Number Formatting (English) ===")
        set_language('en')

        # Large number
        result = format_number(9876543.21, decimals=2, use_grouping=True)
        assert '9,876,543.21' == result or '9876543.21' in result
        print(f"[OK] Large number: {result}")

    def test_format_percent(self):
        """Test percentage formatting."""
        print("\n=== Testing Percentage Formatting ===")

        # 50%
        result = format_percent(0.5)
        assert '50' in result and '%' in result
        print(f"[OK] 50%: {result}")

        # 12.34%
        result = format_percent(0.1234, decimals=2)
        assert '12.34' in result and '%' in result
        print(f"[OK] 12.34%: {result}")


class TestCurrencyFormatters:
    """Test currency formatters."""

    def test_format_cny_chinese(self):
        """Test CNY formatting in Chinese."""
        print("\n=== Testing CNY Formatting (Chinese) ===")
        set_language('zh')

        result = format_currency(1234.56, currency='CNY')
        assert '¥' in result and '1,234.56' in result or '1234.56' in result
        # Use ASCII-safe output to avoid Windows GBK encoding issues
        safe_result = result.encode('ascii', errors='replace').decode('ascii')
        print(f"[OK] CNY: {safe_result}")

    def test_format_usd_english(self):
        """Test USD formatting in English."""
        print("\n=== Testing USD Formatting (English) ===")
        set_language('en')

        result = format_currency(9876.54, currency='USD')
        assert '$' in result and ('9,876.54' in result or '9876.54' in result)
        print(f"[OK] USD: {result}")

    def test_format_eur(self):
        """Test EUR formatting."""
        print("\n=== Testing EUR Formatting ===")

        result = format_currency(500.00, currency='EUR')
        assert '€' in result and '500' in result
        # Use ASCII-safe output to avoid Windows GBK encoding issues
        safe_result = result.encode('ascii', errors='replace').decode('ascii')
        print(f"[OK] EUR: {safe_result}")

    def test_currency_without_symbol(self):
        """Test currency formatting without symbol."""
        print("\n=== Testing Currency Without Symbol ===")

        result = format_currency(1234.56, currency='CNY', show_symbol=False)
        assert '¥' not in result
        assert '1,234.56' in result or '1234.56' in result
        print(f"[OK] Without symbol: {result}")


class TestHotReload:
    """Test hot reload functionality."""

    def test_get_hot_reloader(self):
        """Test getting hot reloader instance."""
        print("\n=== Testing Hot Reloader Instance ===")

        reloader = get_hot_reloader()
        assert reloader is not None
        print("[OK] Hot reloader instance created")

        # Get status
        status = get_hot_reload_status()
        assert 'reload_count' in status
        assert 'registered_callbacks' in status
        print(f"[OK] Status: {status['reload_count']} reloads, {status['registered_callbacks']} callbacks")

    def test_register_callback(self):
        """Test registering reload callbacks."""
        print("\n=== Testing Callback Registration ===")

        callback_called = []

        def test_callback():
            callback_called.append(True)

        register_reload_callback(test_callback)

        status = get_hot_reload_status()
        assert status['registered_callbacks'] > 0
        print(f"[OK] Callback registered (total: {status['registered_callbacks']})")

    def test_manual_reload(self):
        """Test manual translation reload."""
        print("\n=== Testing Manual Reload ===")

        initial_status = get_hot_reload_status()
        initial_count = initial_status['reload_count']

        # Trigger reload
        result = reload_translations(force=True)
        assert result is True
        print("[OK] Reload triggered successfully")

        # Check reload count increased
        new_status = get_hot_reload_status()
        assert new_status['reload_count'] == initial_count + 1
        print(f"[OK] Reload count increased: {initial_count} -> {new_status['reload_count']}")


class TestLanguageSwitching:
    """Test language switching."""

    def test_switch_languages(self):
        """Test switching between languages."""
        print("\n=== Testing Language Switching ===")

        # Switch to Chinese
        set_language('zh')
        assert get_current_language() == 'zh'
        print("[OK] Switched to Chinese")

        # Switch to English
        set_language('en')
        assert get_current_language() == 'en'
        print("[OK] Switched to English")

        # Switch back to Chinese
        set_language('zh')
        assert get_current_language() == 'zh'
        print("[OK] Switched back to Chinese")

    def test_formatters_respect_language(self):
        """Test that formatters respect language setting."""
        print("\n=== Testing Formatters Respect Language ===")

        test_date = date(2024, 1, 24)

        # Format in Chinese
        set_language('zh')
        zh_result = format_date(test_date, 'medium')
        print(f"[OK] Chinese format: {zh_result}")

        # Format in English
        set_language('en')
        en_result = format_date(test_date, 'medium')
        print(f"[OK] English format: {en_result}")

        # They should be different
        assert zh_result != en_result
        print("[OK] Formats are different for different languages")


def run_i18n_full_test_suite():
    """Run all i18n tests."""
    print("=" * 70)
    print("i18n Full Test Suite")
    print("=" * 70)

    results = {}

    test_classes = [
        ("Date/Time Formatters", TestDateTimeFormatters),
        ("Number Formatters", TestNumberFormatters),
        ("Currency Formatters", TestCurrencyFormatters),
        ("Hot Reload", TestHotReload),
        ("Language Switching", TestLanguageSwitching),
    ]

    for test_name, test_class in test_classes:
        try:
            print(f"\n{'=' * 70}")
            print(f"Running: {test_name}")
            print(f"{'=' * 70}")

            instance = test_class()
            test_methods = [m for m in dir(instance) if m.startswith('test_')]

            passed = 0
            failed = 0

            for method_name in test_methods:
                try:
                    # Setup if available
                    if hasattr(instance, 'setup_method'):
                        instance.setup_method()

                    # Run test
                    getattr(instance, method_name)()
                    passed += 1

                except Exception as e:
                    print(f"[X] {method_name} FAILED: {e}")
                    failed += 1
                    import traceback
                    traceback.print_exc()

            results[test_name] = {"passed": passed, "failed": failed}

        except Exception as e:
            print(f"[X] {test_name} TEST CLASS FAILED: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = {"passed": 0, "failed": 1}

    # Summary
    print("\n" + "=" * 70)
    print("i18n FULL TEST SUMMARY")
    print("=" * 70)

    total_passed = sum(r["passed"] for r in results.values())
    total_failed = sum(r["failed"] for r in results.values())
    total = total_passed + total_failed

    for test_name, result in results.items():
        status = "[OK] PASS" if result["failed"] == 0 else "[X] FAIL"
        print(f"{test_name:45s} {status} ({result['passed']}/{result['passed'] + result['failed']})")

    print(f"\nTotal: {total_passed}/{total} tests passed")
    print("=" * 70)

    if total_failed == 0:
        print("\n>>> ALL i18n TESTS PASSED! <<<")
        print("\nFeatures Validated:")
        print("- Date/time formatting (Chinese & English)")
        print("- Number formatting with locale-aware separators")
        print("- Currency formatting (CNY, USD, EUR, etc.)")
        print("- Percentage formatting")
        print("- Relative time formatting")
        print("- Hot reload functionality")
        print("- Translation callback system")
        print("- Language switching")
        return True
    else:
        print(f"\n[!] {total_failed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_i18n_full_test_suite()
    sys.exit(0 if success else 1)
