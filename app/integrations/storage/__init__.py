"""Storage integration package."""

from app.integrations.storage.base import DocumentStorage
from app.integrations.storage.local_storage import LocalDocumentStorage

__all__ = ["DocumentStorage", "LocalDocumentStorage"]
