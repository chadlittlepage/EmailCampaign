"""Tests for email pattern generator"""
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from emailcampaign.pattern_generator import generate_email_patterns, normalize_name


class TestNormalizeName:
    def test_basic_name(self):
        assert normalize_name("John") == "john"

    def test_name_with_spaces(self):
        assert normalize_name("  John  ") == "john"

    def test_name_with_special_chars(self):
        assert normalize_name("John-Paul") == "john paul"

    def test_unicode_name(self):
        # José -> jose
        result = normalize_name("José")
        assert result == "jose"

    def test_empty_name(self):
        assert normalize_name("") == ""

    def test_none_name(self):
        assert normalize_name(None) == ""


class TestGenerateEmailPatterns:
    def test_basic_patterns(self):
        patterns = generate_email_patterns("John", "Smith", "acme.com")
        assert len(patterns) > 0
        assert "john.smith@acme.com" in patterns
        assert "jsmith@acme.com" in patterns

    def test_pattern_order(self):
        patterns = generate_email_patterns("John", "Smith", "acme.com")
        # Most common pattern should be first
        assert patterns[0] == "john.smith@acme.com"

    def test_empty_inputs(self):
        assert generate_email_patterns("", "Smith", "acme.com") == []
        assert generate_email_patterns("John", "", "acme.com") == []
        assert generate_email_patterns("John", "Smith", "") == []

    def test_hyphenated_name(self):
        patterns = generate_email_patterns("Mary", "Smith-Jones", "acme.com")
        assert len(patterns) > 0
        # Should use last part of hyphenated name
        assert "mary.jones@acme.com" in patterns

    def test_multi_part_first_name(self):
        patterns = generate_email_patterns("Mary Jane", "Smith", "acme.com")
        assert len(patterns) > 0
        # Should use first part of first name
        assert "mary.smith@acme.com" in patterns
