"""Development and testing mock security scanner."""

from app.integrations.scanning.base import DocumentSecurityScanner, ScanResult, ScanStatus

# Standard EICAR test string signature for antivirus testing
EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


class MockSecurityScanner(DocumentSecurityScanner):
    """Mock security scanner for testing.

    Detects EICAR test pattern or explicitly tagged malicious files.
    All other valid medical files return CLEAN.
    """

    def __init__(self, scanner_name: str = "MockScanner") -> None:
        self.scanner_name = scanner_name

    async def scan(self, file_bytes: bytes, filename: str) -> ScanResult:
        """Scan file bytes for malicious patterns."""
        if EICAR_SIGNATURE in file_bytes or b"MALICIOUS_VIRUS_TEST" in file_bytes:
            return ScanResult(
                status=ScanStatus.INFECTED,
                scanner=self.scanner_name,
                threat_name="EICAR-Test-Signature",
                message="File matches malicious signature test pattern",
            )
        return ScanResult(
            status=ScanStatus.CLEAN,
            scanner=self.scanner_name,
            message="No threats detected",
        )
