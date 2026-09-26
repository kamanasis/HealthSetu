"""Tests for input validation, path security, and injection defenses."""

import pytest
from app.core.exceptions import ValidationException
from app.core.path_security import is_safe_relative_path, is_safe_storage_key, resolve_safe_path


def test_resolve_safe_path_accepts_clean_relative():
    """Verify that clean relative subpaths are resolved properly."""
    base = "c:/app/data"
    # Using forward slashes works across operating systems with pathlib.Path
    assert is_safe_relative_path(base, "documents/doc1.pdf") is True


def test_resolve_safe_path_rejects_traversal():
    """Verify that traversal paths attempting to escape base directory are rejected."""
    base = "c:/app/data"
    assert is_safe_relative_path(base, "../../windows/system32/cmd.exe") is False
    assert is_safe_relative_path(base, "../../../etc/passwd") is False

    with pytest.raises(ValidationException, match="Path traversal attempt"):
        resolve_safe_path(base, "../../escaped.txt")


def test_is_safe_storage_key():
    """Verify that object storage keys reject dangerous characters and sequences."""
    assert is_safe_storage_key("patients/p-123/documents/d-456.pdf") is True
    assert is_safe_storage_key("../escape/key.pdf") is False
    assert is_safe_storage_key("patients/p-123/../../documents/d-456.pdf") is False
    assert is_safe_storage_key("/leading_slash/doc.pdf") is False
    assert is_safe_storage_key("windows\\backslashes\\doc.pdf") is False
    assert is_safe_storage_key("null\x00byte.pdf") is False
    assert is_safe_storage_key("") is False
