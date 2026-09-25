"""Local storage implementation of DocumentStorage."""

import base64
import os
import secrets
import time
from pathlib import Path

from app.integrations.storage.base import DocumentStorage


class LocalDocumentStorage(DocumentStorage):
    """Local storage provider implementation.

    In testing/dev, operates with in-memory buffer and/or local filesystem.
    Produces short-lived pseudo-signed download tokens.
    """

    def __init__(self, base_dir: str = "data/documents", use_memory: bool = True) -> None:
        self.base_dir = Path(base_dir)
        self.use_memory = use_memory
        self._memory_store: dict[str, tuple[bytes, str]] = {}  # key -> (data, content_type)
        self._tokens: dict[str, tuple[str, float]] = {}  # token -> (key, expiry_timestamp)

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Store bytes under key."""
        self._memory_store[key] = (data, content_type)
        if not self.use_memory:
            target_path = self.base_dir / key
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(data)
        return f"storage://{key}"

    async def get(self, key: str) -> bytes | None:
        """Retrieve bytes by key."""
        if key in self._memory_store:
            return self._memory_store[key][0]
        if not self.use_memory:
            target_path = self.base_dir / key
            if target_path.is_file():
                return target_path.read_bytes()
        return None

    async def delete(self, key: str) -> bool:
        """Delete file by key."""
        existed = key in self._memory_store
        self._memory_store.pop(key, None)
        if not self.use_memory:
            target_path = self.base_dir / key
            if target_path.is_file():
                target_path.unlink()
                existed = True
        return existed

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        if key in self._memory_store:
            return True
        if not self.use_memory:
            return (self.base_dir / key).is_file()
        return False

    async def generate_download_url(
        self, key: str, filename: str, expires_in_seconds: int = 300
    ) -> str:
        """Generate a short-lived download token URL."""
        token = secrets.token_urlsafe(32)
        expiry = time.time() + expires_in_seconds
        self._tokens[token] = (key, expiry)
        return f"/api/v1/documents/download?token={token}&filename={filename}"

    def verify_token(self, token: str) -> str | None:
        """Verify download token and return key if valid and unexpired."""
        entry = self._tokens.get(token)
        if not entry:
            return None
        key, expiry = entry
        if time.time() > expiry:
            self._tokens.pop(token, None)
            return None
        return key

    def clear(self) -> None:
        """Clear all in-memory items (used in testing)."""
        self._memory_store.clear()
        self._tokens.clear()
