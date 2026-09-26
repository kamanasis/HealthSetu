"""Path security and directory traversal protection for HealthSetu.

SECURITY POLICY
================
All filesystem paths and object storage keys constructed from user-supplied
or external input must be validated before access to prevent:
- Local File Inclusion (LFI)
- Directory Traversal attacks (../ or ..\\)
- Null-byte injection
- Absolute path overrides
"""

from __future__ import annotations

import os
from pathlib import Path

from app.core.exceptions import ValidationException


def is_safe_relative_path(base_directory: str | Path, target_path: str | Path) -> bool:
    """Check whether a target path stays strictly inside base_directory without traversing out.

    Args:
        base_directory: The trusted root directory.
        target_path: The untrusted candidate path (relative or absolute).

    Returns:
        True if the resolved path is inside base_directory, False otherwise.
    """
    try:
        base = Path(base_directory).resolve()
        # If target_path is absolute, reject unless it begins with base
        candidate = (base / target_path).resolve()
        return candidate.is_relative_to(base)
    except Exception:
        return False


def resolve_safe_path(base_directory: str | Path, target_path: str | Path) -> Path:
    """Resolve and enforce that target_path stays strictly within base_directory.

    Args:
        base_directory: Trusted root directory.
        target_path: Untrusted path component.

    Returns:
        Resolved absolute Path.

    Raises:
        ValidationException: If traversal out of base directory is detected.
    """
    if not is_safe_relative_path(base_directory, target_path):
        raise ValidationException("Path traversal attempt detected.")

    base = Path(base_directory).resolve()
    return (base / target_path).resolve()


def is_safe_storage_key(key: str) -> bool:
    """Verify that a storage key is safe for cloud/local object stores.

    Rejects keys with:
    - Traversal patterns (.. or /..)
    - Null bytes
    - Leading slashes
    - Windows backslashes
    """
    if not key or not isinstance(key, str):
        return False

    if "\x00" in key:
        return False

    if "\\" in key:
        return False

    if key.startswith("/"):
        return False

    segments = key.split("/")
    for segment in segments:
        if segment in (".", "..") or not segment:
            return False

    return True
