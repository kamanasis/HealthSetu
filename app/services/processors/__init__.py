"""Document processor architecture."""

from app.services.processors.base import DocumentProcessor
from app.services.processors.generic_processor import GenericDocumentProcessor
from app.services.processors.registry import DocumentProcessorRegistry

__all__ = ["DocumentProcessor", "GenericDocumentProcessor", "DocumentProcessorRegistry"]
