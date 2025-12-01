"""Unit tests for student name extraction from program evaluation data."""

import pytest
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.chat_service import _extract_first_name


class TestExtractFirstName:
    """Tests for the _extract_first_name helper function."""

    def test_last_comma_first_with_id(self):
        """Test 'Last,First - ID' format commonly seen in academic records."""
        assert _extract_first_name("Favela,Matt - 2390407") == "Matt"

    def test_last_comma_space_first_with_id(self):
        """Test 'Last, First - ID' format with space after comma."""
        assert _extract_first_name("Favela, Matt - 2390407") == "Matt"

    def test_last_comma_first_no_id(self):
        """Test 'Last, First' format without ID."""
        assert _extract_first_name("Favela, Matt") == "Matt"

    def test_last_comma_first_no_space(self):
        """Test 'Last,First' format without space after comma."""
        assert _extract_first_name("Favela,Matt") == "Matt"

    def test_first_last_format(self):
        """Test 'First Last' format (standard name order)."""
        assert _extract_first_name("Matt Favela") == "Matt"

    def test_single_name(self):
        """Test single name without last name."""
        assert _extract_first_name("Matt") == "Matt"

    def test_empty_string(self):
        """Test empty string returns empty string."""
        assert _extract_first_name("") == ""

    def test_none_returns_empty(self):
        """Test None input returns empty string."""
        assert _extract_first_name(None) == ""

    def test_middle_name_with_id(self):
        """Test name with middle name and ID - should return first name only."""
        assert _extract_first_name("Smith, John Robert - 1234567") == "John"

    def test_whitespace_handling(self):
        """Test that extra whitespace is handled properly."""
        assert _extract_first_name("  Doe , Jane  ") == "Jane"

    def test_multiple_commas(self):
        """Test names with multiple commas (edge case)."""
        # Should take part after first comma
        assert _extract_first_name("Last, First, Middle") == "First"

    def test_hyphenated_first_name(self):
        """Test hyphenated first name - only part before hyphen in ID section."""
        # The hyphen before ID should be handled, not hyphen in name
        assert _extract_first_name("Smith, Mary-Jane - 123") == "Mary-Jane"

    def test_name_with_only_last_and_comma(self):
        """Test edge case where only last name with trailing comma."""
        result = _extract_first_name("Favela,")
        assert result == ""
