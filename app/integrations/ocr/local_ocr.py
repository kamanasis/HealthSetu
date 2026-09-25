"""Local text extraction and OCR adapter."""

import re
from app.integrations.ocr.base import OCRExtractionData, OCRProvider


class LocalOCRProvider(OCRProvider):
    """Local text extraction adapter for testing and lightweight environments.

    Directly parses selectable text from PDF documents and performs
    heuristic text extraction on synthetic images.
    """

    def __init__(self, provider_name: str = "LocalOCR", version: str = "1.0.0") -> None:
        self.provider_name = provider_name
        self.version = version

    async def extract_text(
        self, document_bytes: bytes, mime_type: str, filename: str
    ) -> OCRExtractionData:
        """Extract text from document bytes."""
        if not document_bytes:
            return OCRExtractionData(
                text="",
                confidence=0.0,
                page_count=0,
                provider=self.provider_name,
                provider_version=self.version,
            )

        if mime_type == "application/pdf":
            return self._extract_pdf(document_bytes)
        elif mime_type.startswith("image/"):
            return self._extract_image(document_bytes)
        else:
            # Fallback for plain text / generic files
            try:
                text = document_bytes.decode("utf-8", errors="ignore")
            except Exception:
                text = ""
            return OCRExtractionData(
                text=text.strip(),
                confidence=0.80,
                page_count=1,
                provider=self.provider_name,
                provider_version=self.version,
            )

    def _extract_pdf(self, data: bytes) -> OCRExtractionData:
        """Extract text from PDF streams."""
        # Simple and robust PDF text stream extractor for standard and synthetic test PDFs
        # Looks for text blocks in PDF streams: BT ... ET or plain text strings in parentheses
        text_parts: list[str] = []
        try:
            # Look for literal string chunks between parentheses: (Hello World)
            matches = re.findall(rb"\(([^\(\)\\]{2,})\)", data)
            if matches:
                for m in matches:
                    try:
                        decoded = m.decode("utf-8", errors="ignore").strip()
                        if decoded and not decoded.startswith(("/", "Font", "ProcSet")):
                            text_parts.append(decoded)
                    except Exception:
                        pass

            # Also check if raw utf-8 text is embedded in streams
            if not text_parts:
                decoded_full = data.decode("utf-8", errors="ignore")
                # Look for readable English/medical sentences
                lines = [line.strip() for line in decoded_full.splitlines() if len(line.strip()) > 3]
                filtered = [l for l in lines if not l.startswith(("%", "obj", "endobj", "xref", "trailer"))]
                if filtered:
                    text_parts = filtered[:20]
        except Exception:
            pass

        full_text = "\n".join(text_parts).strip()
        lines = [l for l in full_text.splitlines() if l.strip()]
        return OCRExtractionData(
            text=full_text,
            language="en",
            confidence=0.92 if full_text else 0.50,
            page_count=max(1, data.count(b"/Page\n") or data.count(b"/Page ")),
            provider=self.provider_name,
            provider_version=self.version,
            page_texts=[full_text] if full_text else [],
            raw_lines=lines,
        )

    def _extract_image(self, data: bytes) -> OCRExtractionData:
        """Extract text from image bytes."""
        # In testing/local dev, search for readable UTF-8 text strings inside image payload
        text_parts: list[str] = []
        try:
            decoded = data.decode("utf-8", errors="ignore")
            # Extract printable ASCII sequences
            readable_chunks = re.findall(r"[A-Za-z0-9 ,.:;!?-]{4,}", decoded)
            if readable_chunks:
                text_parts = [c.strip() for c in readable_chunks if len(c.strip()) > 3]
        except Exception:
            pass

        full_text = "\n".join(text_parts).strip()
        return OCRExtractionData(
            text=full_text,
            language="en",
            confidence=0.88 if full_text else 0.40,
            page_count=1,
            provider=self.provider_name,
            provider_version=self.version,
            raw_lines=text_parts,
        )
