"""HL7 Message Validator (Phase 13).

Validates HL7 v2 message structural formatting and header delimiters.
"""

from typing import Any
from app.core.exceptions import InvalidHL7MessageException


class HL7Validator:
    """Validates basic syntax and required segments of HL7 v2 messages."""

    def validate_message(self, raw_message: str) -> list[str]:
        """Validate that the message starts with an MSH segment and contains valid delimiters."""
        errors: list[str] = []
        if not raw_message or not isinstance(raw_message, str):
            return ["HL7 message content must be a non-empty string."]

        trimmed = raw_message.strip()
        if not trimmed.startswith("MSH"):
            errors.append("HL7 message must begin with 'MSH' segment header.")

        if len(trimmed) < 8:
            errors.append("HL7 message header too short to contain valid delimiters.")

        return errors

    def validate_or_raise(self, raw_message: str) -> None:
        """Validate HL7 message and raise InvalidHL7MessageException if invalid."""
        errors = self.validate_message(raw_message)
        if errors:
            raise InvalidHL7MessageException(
                message=f"HL7 message validation failed: {'; '.join(errors)}",
                details={"errors": errors},
            )
