"""Generic medical document processor."""

import re
import uuid
from datetime import datetime, timezone

from app.integrations.ocr.base import OCRProvider
from app.schemas.document import ExtractionResultResponse, StructuredExtractionField
from app.services.processors.base import DocumentProcessor


class GenericDocumentProcessor(DocumentProcessor):
    """General-purpose processor for medical documents.

    Uses the injected OCRProvider for text extraction and extracts
    rudimentary key-value cues without clinical inference or verification.
    """

    def __init__(
        self,
        ocr_provider: OCRProvider,
        name: str = "GenericDocumentProcessor",
        version: str = "1.0.0",
    ) -> None:
        self.ocr_provider = ocr_provider
        self._name = name
        self._version = version

    @property
    def processor_name(self) -> str:
        return self._name

    @property
    def processor_version(self) -> str:
        return self._version

    async def process(
        self, document_id: str, document_bytes: bytes, mime_type: str, filename: str
    ) -> ExtractionResultResponse:
        """Run OCR extraction and compile structured output."""
        ocr_result = await self.ocr_provider.extract_text(
            document_bytes=document_bytes,
            mime_type=mime_type,
            filename=filename,
        )

        # Parse basic structural cues (lines matching 'Key: Value')
        structured_fields: list[StructuredExtractionField] = []
        for line in ocr_result.raw_lines:
            match = re.match(r"^([A-Za-z ]{2,25})\s*[:\-]\s*(.+)$", line)
            if match:
                key, val = match.group(1).strip(), match.group(2).strip()
                structured_fields.append(
                    StructuredExtractionField(
                        field_name=key,
                        raw_value=val,
                        confidence=ocr_result.confidence,
                        page_number=1,
                    )
                )

        now = datetime.now(timezone.utc)
        return ExtractionResultResponse(
            extraction_id=str(uuid.uuid4()),
            document_id=document_id,
            processor=self.processor_name,
            processor_version=self.processor_version,
            extracted_text=ocr_result.text,
            language=ocr_result.language,
            page_count=ocr_result.page_count,
            structured_fields=structured_fields,
            created_at=now,
        )
