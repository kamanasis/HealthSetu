"""Abstract OCR and text extraction provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class OCRExtractionData:
    """Raw extraction result produced by an OCR / text extraction engine."""
    text: str
    language: str = "en"
    confidence: float | None = None
    page_count: int = 1
    provider: str = "local"
    provider_version: str = "1.0.0"
    page_texts: list[str] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)


class OCRProvider(ABC):
    """Abstract interface for text extraction from medical documents."""

    @abstractmethod
    async def extract_text(
        self, document_bytes: bytes, mime_type: str, filename: str
    ) -> OCRExtractionData:
        """Extract text content and layout metadata from raw document bytes.

        Does NOT perform medical diagnosis or clinical interpretation.
        """
        pass
