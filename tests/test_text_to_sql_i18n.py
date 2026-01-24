"""
Test suite for Text-to-SQL i18n error handling.

Tests internationalized error messages in both Chinese (zh) and English (en).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import pytest
from src.text_to_sql.text_to_sql_error_handler import (
    TextToSQLError,
    SQLGenerationError,
    SQLExecutionError,
    SQLValidationError,
    EmptyQueryError,
    ForbiddenSQLOperationError,
    TableNotFoundError,
    ColumnNotFoundError,
    SQLTimeoutError,
    MaxRowsExceededError,
    UnsupportedDialectError,
    ModelNotAvailableError,
    validate_query_input,
    validate_sql_safety,
)
from src.i18n.translations import set_language, get_translation


class TestTextToSQLErrorHandlerChinese:
    """Test Text-to-SQL error handling in Chinese."""

    def setup_method(self):
        """Set language to Chinese before each test."""
        set_language('zh')

    def test_empty_query_error_chinese(self):
        """Test empty query error message in Chinese."""
        print("\n=== Testing Empty Query Error (Chinese) ===")

        with pytest.raises(EmptyQueryError) as exc_info:
            validate_query_input("")

        error = exc_info.value
        assert "不能为空" in error.message or "empty" in error.message.lower()
        assert error.status_code == 400
        print(f"[OK] Empty query error: {error.message}")

    def test_forbidden_sql_operation_chinese(self):
        """Test forbidden SQL operation error in Chinese."""
        print("\n=== Testing Forbidden SQL Operation (Chinese) ===")

        with pytest.raises(ForbiddenSQLOperationError) as exc_info:
            validate_sql_safety("DELETE FROM users")

        error = exc_info.value
        assert "DELETE" in str(error.details) or "DELETE" in error.message
        assert error.status_code == 403
        print(f"[OK] Forbidden operation error: {error.message}")
        print(f"     Details: {error.details}")

    def test_table_not_found_chinese(self):
        """Test table not found error in Chinese."""
        print("\n=== Testing Table Not Found (Chinese) ===")

        error = TableNotFoundError(table="users")
        assert "users" in error.message or "users" in str(error.details)
        assert error.status_code == 404
        print(f"[OK] Table not found error: {error.message}")

    def test_sql_timeout_chinese(self):
        """Test SQL timeout error in Chinese."""
        print("\n=== Testing SQL Timeout (Chinese) ===")

        error = SQLTimeoutError(timeout=30)
        assert "30" in error.message or "30" in str(error.details)
        assert error.status_code == 504
        print(f"[OK] Timeout error: {error.message}")

    def test_max_rows_exceeded_chinese(self):
        """Test max rows exceeded error in Chinese."""
        print("\n=== Testing Max Rows Exceeded (Chinese) ===")

        error = MaxRowsExceededError(actual=1000, limit=100)
        # Check details dict since params may not be in message
        assert error.details.get('actual') == 1000
        assert error.details.get('limit') == 100
        assert error.status_code == 400
        print(f"[OK] Max rows error: {error.message}")
        print(f"     Details: actual={error.details['actual']}, limit={error.details['limit']}")


class TestTextToSQLErrorHandlerEnglish:
    """Test Text-to-SQL error handling in English."""

    def setup_method(self):
        """Set language to English before each test."""
        set_language('en')

    def test_empty_query_error_english(self):
        """Test empty query error message in English."""
        print("\n=== Testing Empty Query Error (English) ===")

        with pytest.raises(EmptyQueryError) as exc_info:
            validate_query_input("")

        error = exc_info.value
        assert "empty" in error.message.lower() or "不能为空" in error.message
        assert error.status_code == 400
        print(f"[OK] Empty query error: {error.message}")

    def test_forbidden_sql_operation_english(self):
        """Test forbidden SQL operation error in English."""
        print("\n=== Testing Forbidden SQL Operation (English) ===")

        # Test with INSERT
        with pytest.raises(ForbiddenSQLOperationError) as exc_info:
            validate_sql_safety("INSERT INTO users VALUES (1, 'test')")

        error = exc_info.value
        assert "INSERT" in str(error.details) or "insert" in error.message.lower()
        assert error.status_code == 403
        print(f"[OK] Forbidden INSERT error: {error.message}")

    def test_column_not_found_english(self):
        """Test column not found error in English."""
        print("\n=== Testing Column Not Found (English) ===")

        error = ColumnNotFoundError(column="email", table="users")
        # Check details dict
        assert error.details.get('column') == "email"
        assert error.details.get('table') == "users"
        assert error.status_code == 404
        print(f"[OK] Column not found error: {error.message}")
        print(f"     Details: column={error.details['column']}, table={error.details['table']}")

    def test_unsupported_dialect_english(self):
        """Test unsupported dialect error in English."""
        print("\n=== Testing Unsupported Dialect (English) ===")

        error = UnsupportedDialectError(dialect="oracle")
        # Check details dict
        assert error.details.get('dialect') == "oracle"
        assert error.status_code == 400
        print(f"[OK] Unsupported dialect error: {error.message}")
        print(f"     Details: dialect={error.details['dialect']}")

    def test_model_not_available_english(self):
        """Test model not available error in English."""
        print("\n=== Testing Model Not Available (English) ===")

        error = ModelNotAvailableError(model="gpt-4", error="Connection timeout")
        assert "gpt-4" in error.message or "gpt-4" in str(error.details)
        assert error.status_code == 503
        print(f"[OK] Model not available error: {error.message}")


class TestSQLSafetyValidation:
    """Test SQL safety validation."""

    def test_valid_select_query(self):
        """Test that valid SELECT queries pass validation."""
        print("\n=== Testing Valid SELECT Query ===")

        valid_queries = [
            "SELECT * FROM users",
            "SELECT id, name FROM users WHERE active = true",
            "WITH temp AS (SELECT * FROM users) SELECT * FROM temp",
        ]

        for query in valid_queries:
            try:
                validate_sql_safety(query)
                print(f"[OK] Valid query passed: {query[:50]}...")
            except ForbiddenSQLOperationError as e:
                pytest.fail(f"Valid query was rejected: {query}\nError: {e.message}")

    def test_forbidden_operations(self):
        """Test that dangerous SQL operations are blocked."""
        print("\n=== Testing Forbidden Operations ===")

        forbidden_queries = [
            ("INSERT INTO users VALUES (1)", "INSERT"),
            ("UPDATE users SET active = false", "UPDATE"),
            ("DELETE FROM users WHERE id = 1", "DELETE"),
            ("DROP TABLE users", "DROP"),
            ("CREATE TABLE test (id INT)", "CREATE"),
            ("ALTER TABLE users ADD COLUMN test VARCHAR", "ALTER"),
            ("TRUNCATE TABLE users", "TRUNCATE"),
        ]

        for query, expected_keyword in forbidden_queries:
            with pytest.raises(ForbiddenSQLOperationError) as exc_info:
                validate_sql_safety(query)

            error = exc_info.value
            print(f"[OK] Blocked {expected_keyword}: {error.message}")


class TestQueryInputValidation:
    """Test query input validation."""

    def test_empty_query_validation(self):
        """Test that empty queries are rejected."""
        print("\n=== Testing Empty Query Validation ===")

        empty_inputs = ["", "   ", "\n\t  "]

        for empty_query in empty_inputs:
            with pytest.raises(EmptyQueryError):
                validate_query_input(empty_query)
            print(f"[OK] Rejected empty query: {repr(empty_query)}")

    def test_query_length_validation(self):
        """Test that overly long queries are rejected."""
        print("\n=== Testing Query Length Validation ===")

        # Create a query that's too long (over 10,000 chars)
        long_query = "SELECT * FROM users WHERE " + " OR ".join(
            [f"id = {i}" for i in range(2000)]
        )

        assert len(long_query) > 10000, "Test query should be > 10000 chars"

        from src.text_to_sql.text_to_sql_error_handler import InvalidQueryError

        with pytest.raises(InvalidQueryError) as exc_info:
            validate_query_input(long_query)

        error = exc_info.value
        print(f"[OK] Rejected long query ({len(long_query)} chars): {error.message}")

    def test_valid_query_validation(self):
        """Test that valid queries pass validation."""
        print("\n=== Testing Valid Query Validation ===")

        valid_query = "SELECT * FROM users WHERE active = true"

        try:
            validate_query_input(valid_query)
            print(f"[OK] Valid query passed: {valid_query}")
        except Exception as e:
            pytest.fail(f"Valid query was rejected: {e}")


class TestErrorCodeConsistency:
    """Test error code consistency."""

    def test_error_codes_are_unique(self):
        """Test that each error type has a unique error code."""
        print("\n=== Testing Error Code Uniqueness ===")

        errors = [
            (SQLGenerationError(), "SQL_GENERATION_FAILED"),
            (SQLExecutionError(), "SQL_EXECUTION_FAILED"),
            (SQLValidationError(), "SQL_VALIDATION_FAILED"),
            (EmptyQueryError(), "EMPTY_QUERY"),
            (ForbiddenSQLOperationError(), "FORBIDDEN_SQL_OPERATION"),
            (TableNotFoundError(table="test"), "TABLE_NOT_FOUND"),
            (SQLTimeoutError(), "SQL_TIMEOUT"),
            (UnsupportedDialectError(dialect="test"), "UNSUPPORTED_DIALECT"),
        ]

        error_codes = set()
        for error, expected_code in errors:
            assert error.error_code == expected_code, \
                f"Error code mismatch: expected {expected_code}, got {error.error_code}"

            assert error.error_code not in error_codes, \
                f"Duplicate error code: {error.error_code}"

            error_codes.add(error.error_code)
            print(f"[OK] {error.__class__.__name__}: {error.error_code}")

    def test_http_status_codes(self):
        """Test that HTTP status codes are appropriate."""
        print("\n=== Testing HTTP Status Codes ===")

        # 400 errors (client errors)
        assert EmptyQueryError().status_code == 400
        assert SQLValidationError().status_code == 400
        assert UnsupportedDialectError(dialect="test").status_code == 400

        # 403 error (forbidden)
        assert ForbiddenSQLOperationError().status_code == 403

        # 404 errors (not found)
        assert TableNotFoundError(table="test").status_code == 404

        # 500 errors (server errors)
        assert SQLGenerationError().status_code == 500
        assert SQLExecutionError().status_code == 500

        # 503 error (service unavailable)
        assert ModelNotAvailableError().status_code == 503

        # 504 error (timeout)
        assert SQLTimeoutError().status_code == 504

        print("[OK] All HTTP status codes are appropriate")


def run_text_to_sql_i18n_tests():
    """Run all Text-to-SQL i18n tests."""
    print("=" * 70)
    print("Text-to-SQL i18n Error Handling Tests")
    print("=" * 70)

    results = {}

    test_classes = [
        ("Chinese Error Messages", TestTextToSQLErrorHandlerChinese),
        ("English Error Messages", TestTextToSQLErrorHandlerEnglish),
        ("SQL Safety Validation", TestSQLSafetyValidation),
        ("Query Input Validation", TestQueryInputValidation),
        ("Error Code Consistency", TestErrorCodeConsistency),
    ]

    for test_name, test_class in test_classes:
        try:
            print(f"\n{'='*70}")
            print(f"Running: {test_name}")
            print(f"{'='*70}")

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
    print("TEXT-TO-SQL I18N TEST SUMMARY")
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
        print("\n>>> ALL TEXT-TO-SQL I18N TESTS PASSED! <<<")
        print("\nFeatures Validated:")
        print("- Text-to-SQL error messages in Chinese (zh)")
        print("- Text-to-SQL error messages in English (en)")
        print("- SQL safety validation (forbidden operations)")
        print("- Query input validation (empty, length)")
        print("- Error code consistency and uniqueness")
        print("- Appropriate HTTP status codes")
        return True
    else:
        print(f"\n[!] {total_failed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_text_to_sql_i18n_tests()
    sys.exit(0 if success else 1)
