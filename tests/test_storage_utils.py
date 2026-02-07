"""Tests for storage utility functions."""

from ljs.storage.jobs import _build_ml_text, _normalize_whitespace, _redact_pii


class TestNormalizeWhitespace:
    """Test whitespace normalization utility."""

    def test_normalize_spaces(self) -> None:
        """Test collapsing multiple spaces."""
        text = "hello    world"
        result = _normalize_whitespace(text)
        assert result == "hello world"

    def test_normalize_tabs(self) -> None:
        """Test converting tabs to spaces."""
        text = "hello\t\tworld"
        result = _normalize_whitespace(text)
        assert result == "hello world"

    def test_normalize_newlines(self) -> None:
        """Test collapsing multiple newlines."""
        text = "hello\n\n\n\nworld"
        result = _normalize_whitespace(text)
        assert result == "hello\n\nworld"

    def test_normalize_crlf(self) -> None:
        """Test converting CRLF to LF."""
        text = "hello\r\nworld"
        result = _normalize_whitespace(text)
        assert result == "hello\nworld"

    def test_normalize_strips(self) -> None:
        """Test stripping leading/trailing whitespace."""
        text = "  hello world  "
        result = _normalize_whitespace(text)
        assert result == "hello world"

    def test_normalize_mixed(self) -> None:
        """Test normalizing mixed whitespace."""
        text = "  hello   \t  world  \n\n\n\n  foo  "
        result = _normalize_whitespace(text)
        # Verify multiple spaces/tabs are collapsed and extra newlines reduced
        assert "\t" not in result
        assert "\n\n\n" not in result


class TestRedactPii:
    """Test PII redaction utility."""

    def test_redact_email(self) -> None:
        """Test email redaction."""
        text = "Contact us at hr@example.com for details."
        result = _redact_pii(text)
        assert "[EMAIL]" in result
        assert "hr@example.com" not in result

    def test_redact_multiple_emails(self) -> None:
        """Test multiple email redaction."""
        text = "Email john@test.com or jane@company.org"
        result = _redact_pii(text)
        assert result.count("[EMAIL]") == 2

    def test_redact_phone_international(self) -> None:
        """Test international phone number redaction."""
        text = "Call +1 (555) 123-4567 now"
        result = _redact_pii(text)
        assert "[PHONE]" in result

    def test_redact_phone_with_dashes(self) -> None:
        """Test phone with dashes redaction."""
        text = "Phone: 555-123-4567"
        result = _redact_pii(text)
        assert "[PHONE]" in result

    def test_preserve_short_numbers(self) -> None:
        """Test that short numbers are not redacted as phones."""
        text = "We have 5 years experience"
        result = _redact_pii(text)
        assert "5" in result
        assert "[PHONE]" not in result

    def test_preserve_phone_like_with_few_digits(self) -> None:
        """Test phone-like text with <10 digits is preserved."""
        text = "Call +1 (23) 45-67-89 for info."
        result = _redact_pii(text)
        assert "[PHONE]" not in result
        assert "+1 (23) 45-67-89" in result

    def test_preserve_all_digit_sequences(self) -> None:
        """Test that plain digit sequences are preserved."""
        text = "Job ID: 1234567890"
        result = _redact_pii(text)
        assert "1234567890" in result

    def test_no_pii_unchanged(self) -> None:
        """Test text without PII is unchanged."""
        text = "This is a regular job description."
        result = _redact_pii(text)
        assert result == text


class TestBuildMlText:
    """Test ML text building utility."""

    def test_build_all_fields(self) -> None:
        """Test building text with all fields."""
        result = _build_ml_text(
            title="Software Engineer",
            company_name="Tech Corp",
            location="Berlin",
            description="Great job opportunity.",
        )
        assert "Software Engineer" in result
        assert "Tech Corp" in result
        assert "Berlin" in result
        assert "Great job opportunity" in result

    def test_build_partial_fields(self) -> None:
        """Test building text with some fields missing."""
        result = _build_ml_text(
            title="Engineer",
            company_name=None,
            location="Berlin",
            description=None,
        )
        assert "Engineer" in result
        assert "Berlin" in result

    def test_build_empty_fields(self) -> None:
        """Test building text with all empty fields."""
        result = _build_ml_text(
            title=None,
            company_name=None,
            location=None,
            description=None,
        )
        assert result == ""

    def test_build_separates_with_newlines(self) -> None:
        """Test that fields are separated by double newlines."""
        result = _build_ml_text(
            title="Title",
            company_name="Company",
            location=None,
            description=None,
        )
        assert "\n\n" in result
