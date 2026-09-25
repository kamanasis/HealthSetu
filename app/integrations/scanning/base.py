"""Abstract malware and security scanning interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class ScanStatus(str, Enum):
    """Malware scanning result status."""
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"


@dataclass
class ScanResult:
    """Security scanner evaluation result."""
    status: ScanStatus
    scanner: str
    threat_name: str | None = None
    message: str | None = None

    @property
    def is_safe(self) -> bool:
        return self.status == ScanStatus.CLEAN


class DocumentSecurityScanner(ABC):
    """Abstract interface for malware/virus security scanning of uploaded files."""

    @abstractmethod
    async def scan(self, file_bytes: bytes, filename: str) -> ScanResult:
        """Scan file bytes for malicious content."""
        pass
