"""AI Security, Prompt Injection Defense, and PHI Minimization (Phase 14).

Enforces:
1. Strict delimiter isolation of untrusted clinical texts.
2. Adversarial prompt injection pattern detection and neutralization.
3. PHI and credential minimization prior to model dispatch.
"""

import re
from typing import Any

from app.core.exceptions import PromptInjectionDetectedException

# Delimiters used to safely isolate untrusted source text in prompts
SOURCE_START_DELIMITER = "<<<SOURCE_START>>>"
SOURCE_END_DELIMITER = "<<<SOURCE_END>>>"

# Known adversarial prompt injection heuristics
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+(directives?|directions?|instructions?)", re.IGNORECASE),
    re.compile(r"(you\s+are\s+now|act\s+as)\s+(an?\s+)?(unrestricted|jailbroken|dan|evil)", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+must", re.IGNORECASE),
    re.compile(r"bypass\s+(all\s+)?(safety|clinical|security)\s+(rules?|guidelines?|policies?|filters?)", re.IGNORECASE),
    re.compile(r"reveal\s+(the\s+|your\s+)?(system\s+prompt|instructions?|secret\s+key|password)", re.IGNORECASE),
    re.compile(r"repeat\s+(everything|the\s+words)\s+above", re.IGNORECASE),
]

# Sensitive credentials that must NEVER enter prompts
_FORBIDDEN_KEYWORDS = [
    "password", "bearer ", "eyj", "secret_key", "api_key", "access_token",
    "private_key", "-----begin", "authorization:"
]


class AISecurityValidator:
    """Security guardrails applied before prompts are assembled and dispatched."""

    @classmethod
    def detect_prompt_injection(cls, text: str) -> None:
        """Scan text for prompt injection patterns and raise PromptInjectionDetectedException if found."""
        cls.sanitize_untrusted_text(text, block_on_injection=True)

    @classmethod
    def sanitize_untrusted_text(cls, text: str, block_on_injection: bool = True) -> str:
        """Sanitize untrusted text and neutralize delimiter tampering or injection attempts."""
        if not text:
            return ""

        # 1. Delimiter Escaping: prevent adversary from breaking out of delimiter boundary
        sanitized = text.replace(SOURCE_START_DELIMITER, "[ESCAPED_SOURCE_START]")
        sanitized = sanitized.replace(SOURCE_END_DELIMITER, "[ESCAPED_SOURCE_END]")

        # 2. Check for adversarial injection patterns
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(sanitized):
                if block_on_injection:
                    raise PromptInjectionDetectedException(
                        message="Potential prompt injection instruction detected in source document."
                    )
                else:
                    # Neutralize pattern safely
                    sanitized = pattern.sub("[FILTERED_INSTRUCTION]", sanitized)

        # 3. Check for leaked credentials or secrets
        lower_text = sanitized.lower()
        for forbidden in _FORBIDDEN_KEYWORDS:
            if forbidden in lower_text:
                # Mask out obvious tokens
                sanitized = re.sub(
                    re.escape(forbidden) + r"[^\s,;]+",
                    "[REDACTED_CREDENTIAL]",
                    sanitized,
                    flags=re.IGNORECASE,
                )

        return sanitized

    @classmethod
    def minimize_phi(cls, data: dict[str, Any], allowed_fields: set[str] | None = None) -> dict[str, Any]:
        """Strip unnecessary identifiers and non-essential fields from payload."""
        minimized: dict[str, Any] = {}
        for key, value in data.items():
            k_lower = key.lower()
            # Drop credentials and internal authorization data
            if any(f in k_lower for f in ("token", "secret", "password", "hash", "session", "jwt")):
                continue

            if allowed_fields is not None and key not in allowed_fields:
                continue

            if isinstance(value, dict):
                minimized[key] = cls.minimize_phi(value)
            elif isinstance(value, list):
                minimized[key] = [
                    cls.minimize_phi(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                minimized[key] = value

        return minimized

    @classmethod
    def wrap_source_content(cls, content: str) -> str:
        """Wrap untrusted source text safely inside designated boundary markers."""
        cleaned = cls.sanitize_untrusted_text(content, block_on_injection=True)
        return f"{SOURCE_START_DELIMITER}\n{cleaned}\n{SOURCE_END_DELIMITER}"
