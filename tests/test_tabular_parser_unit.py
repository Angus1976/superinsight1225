"""
Unit tests for TabularParser.

Tests CSV/Excel parsing, validation, encoding handling, and error cases
as specified in Requirements 1.3 and design.md TabularParser spec.
"""

import os
import tempfile

import pandas as pd
import pytest

from src.extractors.tabular import TabularData, TabularParser


@pytest.fixture
def parser():
    return TabularParser()


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

class TestParseCSV:
    """Tests for CSV file parsing."""

    def test_basic_csv(self, parser, tmp_path):
        csv_file = tmp_path / "basic.csv"
        csv_file.write_text("name,age,city\nAlice,30,Beijing\nBob,25,Shanghai\n")

        result = parser.parse(str(csv_file), "csv")

        assert isinstance(result, TabularData)
        assert result.headers == ["name", "age", "city"]
        assert result.row_count == 2
        assert len(result.rows) == 2
        assert result.rows[0] == {"name": "Alice", "age": 30, "city": "Beijing"}
        assert result.file_type == "csv"
        assert result.sheet_name is None

    def test_single_row_csv(self, parser, tmp_path):
        csv_file = tmp_path / "single.csv"
        csv_file.write_text("id,value\n1,hello\n")

        result = parser.parse(str(csv_file), "csv")

        assert result.row_count == 1
        assert result.rows[0] == {"id": 1, "value": "hello"}

    def test_csv_with_missing_values(self, parser, tmp_path):
        csv_file = tmp_path / "missing.csv"
        csv_file.write_text("a,b,c\n1,,3\n,5,\n")

        result = parser.parse(str(csv_file), "csv")

        assert result.row_count == 2
        # NaN replaced with None
        assert result.rows[0]["b"] is None
        assert result.rows[1]["a"] is None
        assert result.rows[1]["c"] is None

    def test_csv_latin1_fallback(self, parser, tmp_path):
        csv_file = tmp_path / "latin1.csv"
        csv_file.write_bytes(b"name,city\nJos\xe9,M\xe9xico\n")

        result = parser.parse(str(csv_file), "csv")

        assert result.row_count == 1
        assert result.rows[0]["name"] == "José"

    def test_row_keys_match_headers(self, parser, tmp_path):
        csv_file = tmp_path / "keys.csv"
        csv_file.write_text("x,y,z\n1,2,3\n4,5,6\n")

        result = parser.parse(str(csv_file), "csv")

        for row in result.rows:
            assert set(row.keys()) == set(result.headers)


# ---------------------------------------------------------------------------
# Excel parsing
# ---------------------------------------------------------------------------

class TestParseExcel:
    """Tests for Excel file parsing."""

    def test_basic_excel(self, parser, tmp_path):
        xlsx_file = tmp_path / "basic.xlsx"
        df = pd.DataFrame({"name": ["Alice", "Bob"], "score": [90, 85]})
        df.to_excel(str(xlsx_file), index=False, engine="openpyxl")

        result = parser.parse(str(xlsx_file), "excel")

        assert isinstance(result, TabularData)
        assert result.headers == ["name", "score"]
        assert result.row_count == 2
        assert result.file_type == "excel"
        assert result.sheet_name is not None

    def test_excel_row_keys_match_headers(self, parser, tmp_path):
        xlsx_file = tmp_path / "keys.xlsx"
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        df.to_excel(str(xlsx_file), index=False, engine="openpyxl")

        result = parser.parse(str(xlsx_file), "excel")

        for row in result.rows:
            assert set(row.keys()) == set(result.headers)


# ---------------------------------------------------------------------------
# Validation & error handling
# ---------------------------------------------------------------------------

class TestValidation:
    """Tests for input validation and error handling."""

    def test_invalid_file_type_raises(self, parser, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("a\n1\n")

        with pytest.raises(ValueError, match="Unsupported file_type"):
            parser.parse(str(f), "json")

    def test_nonexistent_file_raises(self, parser):
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/path.csv", "csv")

    def test_empty_file_raises(self, parser, tmp_path):
        f = tmp_path / "empty.csv"
        f.write_text("")

        with pytest.raises(ValueError, match="empty"):
            parser.parse(str(f), "csv")

    def test_file_size_limit(self, parser, tmp_path):
        """Verify files > 100MB are rejected."""
        big = tmp_path / "big.csv"
        big.write_text("x\n")

        # Patch os.path.getsize to simulate a large file
        import unittest.mock as mock
        with mock.patch("src.extractors.tabular.os.path.getsize", return_value=200 * 1024 * 1024):
            with pytest.raises(ValueError, match="exceeds"):
                parser.parse(str(big), "csv")

    def test_corrupted_excel_raises_runtime(self, parser, tmp_path):
        """Non-Excel file with .xlsx extension should raise RuntimeError."""
        f = tmp_path / "corrupt.xlsx"
        f.write_bytes(b"this is not an excel file")

        with pytest.raises(RuntimeError):
            parser.parse(str(f), "excel")


# ---------------------------------------------------------------------------
# Postcondition: row_count == len(rows)
# ---------------------------------------------------------------------------

class TestPostconditions:
    """Verify formal postconditions from design.md."""

    def test_row_count_equals_len_rows_csv(self, parser, tmp_path):
        f = tmp_path / "pc.csv"
        f.write_text("a,b\n1,2\n3,4\n5,6\n")

        result = parser.parse(str(f), "csv")

        assert result.row_count == len(result.rows)

    def test_row_count_equals_len_rows_excel(self, parser, tmp_path):
        f = tmp_path / "pc.xlsx"
        df = pd.DataFrame({"x": range(10)})
        df.to_excel(str(f), index=False, engine="openpyxl")

        result = parser.parse(str(f), "excel")

        assert result.row_count == len(result.rows)

    def test_headers_non_empty(self, parser, tmp_path):
        f = tmp_path / "h.csv"
        f.write_text("col1,col2\n1,2\n")

        result = parser.parse(str(f), "csv")

        assert len(result.headers) > 0
