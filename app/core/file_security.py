"""File upload security and content verification for HealthSetu.

SECURITY POLICY
================
All user-uploaded files must undergo rigorous validation before acceptance:
1. Magic bytes verification to prevent MIME-type spoofing
2. Filename sanitization and path traversal detection
3. Size limits enforcement
4. Extension-to-MIME alignment verification
5. Generation of cryptographically random storage keys (never trust client filenames)
"""

from __future__ import annotations

import os
import re
import uuid
from typing import Final

from app.core.exceptions import ValidationException

# ---------------------------------------------------------------------------
# Allowed MIME types and corresponding acceptable extensions
# ---------------------------------------------------------------------------
ALLOWED_FILE_TYPES: Final[dict[str, list[str]]] = {
    "application/pdf": [".pdf"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
    "application/dicom": [".dcm", ".dicom"],
}

# ---------------------------------------------------------------------------
# Magic bytes signatures for MIME verification
# (offset, signature_bytes, mime_type)
# ---------------------------------------------------------------------------
MAGIC_SIGNATURES: Final[list[tuple[int, bytes, str]]] = [
    (0, b"%PDF", "application/pdf"),
    (0, b"\xff\xd8\xff", "image/jpeg"),
    (0, b"\x89PNG\r\n\x1a\n", "image/png"),
    (0, b"RIFF", "image/webp"),
    (128, b"DICM", "application/dicom"),  # DICOM header is preceded by 128-byte preamble
]

_PATH_TRAVERSAL_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"\.\.[/\\]"),          # ../ or ..\
    re.compile(r"[/\\]\.\."),          # /.. or \..
    re.compile(r"^\.\.$"),             # exact ..
    re.compile(r"\x00"),               # Null byte
    re.compile(r"^[a-zA-Z]:[/\\]"),    # Windows drive letter (e.g., C:\)
    re.compile(r"^/"),                 # Unix absolute path
    re.compile(r"^\\"),                # Windows absolute path or UNC
]

_DANGEROUS_EXTENSIONS: Final[frozenset[str]] = frozenset({
    ".exe", ".bat", ".cmd", ".sh", ".bash", ".ps1", ".vbs", ".js", ".ts",
    ".php", ".py", ".rb", ".pl", ".cgi", ".jar", ".war", ".jsp", ".asp",
    ".aspx", ".dll", ".so", ".dylib", ".bin", ".scr", ".pif", ".hta",
})


def detect_path_traversal(name: str) -> bool:
    """Check if a filename or path contains traversal patterns or null bytes.

    Args:
        name: Filename or path component to inspect.

    Returns:
        True if suspicious or dangerous path traversal patterns are found.
    """
    if not name or not isinstance(name, str):
        return False

    for pattern in _PATH_TRAVERSAL_PATTERNS:
        if pattern.search(name):
            return True

    # Also detect encoded variations (%2e%2e, %2f, etc.)
    lower = name.lower()
    if "%2e" in lower or "%2f" in lower or "%5c" in lower:
        return True

    return False


def sanitize_filename(filename: str, fallback_prefix: str = "doc") -> str:
    """Sanitize user-provided filename by stripping directories and special characters.

    Args:
        filename: Raw client-provided filename.
        fallback_prefix: Prefix used if sanitized result is empty.

    Returns:
        Safe, sanitized filename string.
    """
    if not filename:
        return f"{fallback_prefix}_{uuid.uuid4().hex[:8]}"

    # Extract base filename (removes directory components)
    clean = os.path.basename(filename.strip())

    # Replace all characters except alphanumeric, period, hyphen, and underscore
    clean = re.sub(r"[^A-Za-z0-9._-]", "_", clean)

    # Disallow leading periods (hidden files) or multiple consecutive periods
    clean = re.sub(r"^\.+", "", clean)
    clean = re.sub(r"\.{2,}", ".", clean)

    if not clean or clean.startswith("."):
        clean = f"{fallback_prefix}_{uuid.uuid4().hex[:8]}"

    # Ensure dangerous extensions are rejected or stripped
    _, ext = os.path.splitext(clean.lower())
    if ext in _DANGEROUS_EXTENSIONS:
        clean = f"{clean}.blocked"

    return clean[:255]


def verify_magic_bytes(file_bytes: bytes, expected_mime: str) -> bool:
    """Verify that file content header matches declared MIME type.

    Args:
        file_bytes: Binary payload of the file.
        expected_mime: Declared MIME type (e.g. 'application/pdf').

    Returns:
        True if magic bytes match or format does not require binary signature.
    """
    if not file_bytes:
        return False

    normalized_mime = expected_mime.lower().strip()

    # Find matching signature for this MIME type
    signatures_for_mime = [
        (offset, sig) for offset, sig, mime in MAGIC_SIGNATURES if mime == normalized_mime
    ]

    if not signatures_for_mime:
        # MIME type not in signature table
        return False

    for offset, sig in signatures_for_mime:
        if len(file_bytes) >= offset + len(sig):
            if file_bytes[offset : offset + len(sig)] == sig:
                return True

    return False


def generate_safe_storage_key(patient_id: str, document_id: str, extension: str) -> str:
    """Generate a predictable, safe, collision-resistant object storage key.

    Never uses user-supplied filenames in object storage keys.

    Args:
        patient_id: UUID of patient.
        document_id: UUID of document record.
        extension: Validated file extension (e.g. '.pdf').

    Returns:
        Storage key path string: patients/{patient_id}/documents/{document_id}{ext}
    """
    clean_ext = extension.lower().strip()
    if not clean_ext.startswith("."):
        clean_ext = f".{clean_ext}"

    # Disallow path traversal in IDs
    if detect_path_traversal(patient_id) or detect_path_traversal(document_id):
        raise ValidationException("Invalid identifiers for document storage key.")

    return f"patients/{patient_id}/documents/{document_id}{clean_ext}"


def validate_file_upload_security(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    max_size_bytes: int = 20 * 1024 * 1024,
) -> tuple[str, str]:
    """Perform complete Phase 15 security validation on an uploaded file.

    Args:
        file_bytes: Raw bytes of uploaded file.
        filename: Name supplied by client.
        content_type: Content-Type header supplied by client.
        max_size_bytes: Maximum permitted size in bytes.

    Returns:
        Tuple of (sanitized_filename, validated_mime_type).

    Raises:
        ValidationException: If any security check fails.
    """
    if not file_bytes:
        raise ValidationException("Uploaded file is empty.")

    if len(file_bytes) > max_size_bytes:
        raise ValidationException(
            f"File size ({len(file_bytes)} bytes) exceeds the maximum allowed limit of {max_size_bytes} bytes."
        )

    if detect_path_traversal(filename):
        raise ValidationException("Path traversal pattern detected in filename.")

    sanitized_name = sanitize_filename(filename)

    normalized_mime = content_type.lower().strip()
    if normalized_mime not in ALLOWED_FILE_TYPES:
        raise ValidationException(
            f"Unsupported document MIME type '{content_type}'. Allowed types: {list(ALLOWED_FILE_TYPES.keys())}"
        )

    # Check extension against allowed extensions for this MIME
    _, ext = os.path.splitext(sanitized_name.lower())
    if ext and ext not in ALLOWED_FILE_TYPES[normalized_mime]:
        raise ValidationException(
            f"File extension '{ext}' does not match content type '{normalized_mime}'."
        )

    # Magic byte check
    if not verify_magic_bytes(file_bytes, normalized_mime):
        raise ValidationException(
            f"File content signature does not match declared MIME type '{normalized_mime}'."
        )

    return sanitized_name, normalized_mime
