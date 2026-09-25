"""Document processor registry."""

from app.schemas.document import DocumentType
from app.services.processors.base import DocumentProcessor
from app.services.processors.generic_processor import GenericDocumentProcessor


class DocumentProcessorRegistry:
    """Registry routing document types to specific document processors."""

    def __init__(self, default_processor: DocumentProcessor) -> None:
        self.default_processor = default_processor
        self._registry: dict[DocumentType, DocumentProcessor] = {}

    def register(self, doc_type: DocumentType, processor: DocumentProcessor) -> None:
        """Register specialized processor for a document type."""
        self._registry[doc_type] = processor

    def get_processor(self, doc_type: DocumentType) -> DocumentProcessor:
        """Retrieve processor for document type, falling back to default."""
        return self._registry.get(doc_type, self.default_processor)
