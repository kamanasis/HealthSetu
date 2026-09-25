"""Abstract object storage interface for medical documents."""

from abc import ABC, abstractmethod


class DocumentStorage(ABC):
    """Abstract object/blob storage provider interface.

    Decouples document processing and persistence from specific cloud or local storage providers.
    """

    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Store binary document data under a unique key.

        Returns storage URI or internal reference.
        """
        pass

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        """Retrieve binary document data by key. Returns None if not found."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete document from storage. Returns True if deleted."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check whether an object exists under the key."""
        pass

    @abstractmethod
    async def generate_download_url(
        self, key: str, filename: str, expires_in_seconds: int = 300
    ) -> str:
        """Generate a short-lived, controlled download URL or signed token."""
        pass
