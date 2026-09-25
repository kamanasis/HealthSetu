"""OCR integration package."""

from app.integrations.ocr.base import OCRExtractionData, OCRProvider
from app.integrations.ocr.local_ocr import LocalOCRProvider

__all__ = ["OCRExtractionData", "OCRProvider", "LocalOCRProvider"]
