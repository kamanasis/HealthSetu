"""Tests for file upload security, magic bytes verification, and path traversal."""

import pytest
from app.core.exceptions import ValidationException
from app.core.file_security import (
    detect_path_traversal,
    generate_safe_storage_key,
    sanitize_filename,
    validate_file_upload_security,
    verify_magic_bytes,
)


def test_valid_pdf_magic_bytes():
    """Verify that a valid PDF payload passes validation."""
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    name, mime = validate_file_upload_security(
        pdf_bytes, "lab_report.pdf", "application/pdf", max_size_bytes=1024 * 1024
    )
    assert name == "lab_report.pdf"
    assert mime == "application/pdf"


def test_valid_image_magic_bytes():
    """Verify JPEG and PNG magic bytes detection."""
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 20
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 20

    assert verify_magic_bytes(jpeg_bytes, "image/jpeg") is True
    assert verify_magic_bytes(png_bytes, "image/png") is True


def test_spoofed_mime_type_rejected():
    """Verify that plain text or shell script masquerading as PDF is rejected."""
    fake_pdf = b"echo 'Malicious shell script masquerading as pdf'"
    with pytest.raises(ValidationException, match="signature does not match"):
        validate_file_upload_security(
            fake_pdf, "report.pdf", "application/pdf", max_size_bytes=1024 * 1024
        )


def test_detect_path_traversal_patterns():
    """Verify detection of traversal patterns."""
    assert detect_path_traversal("../../etc/shadow") is True
    assert detect_path_traversal("..\\windows\\system32") is True
    assert detect_path_traversal("/absolute/path") is True
    assert detect_path_traversal("C:\\boot.ini") is True
    assert detect_path_traversal("file\x00name.pdf") is True
    assert detect_path_traversal("safe_report_2026.pdf") is False


def test_sanitize_filename_strips_traversal():
    """Verify that filename sanitization neutralizes traversal sequences."""
    sanitized = sanitize_filename("../../malicious_file.pdf")
    assert ".." not in sanitized
    assert "/" not in sanitized
    assert sanitized == "malicious_file.pdf"


def test_dangerous_extension_blocked():
    """Verify that executable scripts are neutralized."""
    sanitized = sanitize_filename("script.exe")
    assert sanitized.endswith(".blocked")


def test_generate_safe_storage_key():
    """Verify structured non-user-controlled storage key generation."""
    key = generate_safe_storage_key("patient-123", "doc-456", ".pdf")
    assert key == "patients/patient-123/documents/doc-456.pdf"

    # Traversal in patient_id or document_id is rejected
    with pytest.raises(ValidationException):
        generate_safe_storage_key("../escape", "doc-456", ".pdf")


def test_file_size_limit_enforced():
    """Verify that oversized files are rejected."""
    huge_bytes = b"%PDF" + b"A" * 2000
    with pytest.raises(ValidationException, match="exceeds the maximum allowed limit"):
        validate_file_upload_security(
            huge_bytes, "doc.pdf", "application/pdf", max_size_bytes=500
        )
