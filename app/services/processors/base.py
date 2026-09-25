"""Abstract document processor interface."""

from abc import ABC, abstractmethod
from app.schemas.document import ExtractionResultResponse


class DocumentProcessor(ABC):
    """Abstract interface for document processors."""

    @property
    @abstractmethod
    def processor_name(self) -> str:
        pass

    @property
    @abstractmethod
    def processor_version(self) -> str:
        pass

    @abstractmethod
    async def process(
        self, document_id: str, document_bytes: bytes, mime_type: str, filename: str
    ) -> ExtractionResultResponse:
        """Process document bytes and return structured extraction result."""
        pass
