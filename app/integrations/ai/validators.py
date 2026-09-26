"""Structured output and JSON parsing validators for AI response payloads."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from app.core.exceptions import AIOutputInvalidException, AIOutputSchemaInvalidException

T = TypeVar("T", bound=BaseModel)


class AIOutputValidator:
    """Validates raw AI text outputs against JSON and expected Pydantic schemas."""

    @staticmethod
    def extract_json(raw_text: str) -> Dict[str, Any]:
        """Extract and parse a JSON dictionary from raw model text.
        
        Handles:
        - Plain JSON objects
        - Markdown fenced code blocks: ```json ... ``` or ``` ... ```
        - Leading/trailing whitespace
        """
        if not raw_text or not raw_text.strip():
            raise AIOutputInvalidException("Raw model response was empty.")

        text = raw_text.strip()

        # Handle ```json ... ``` blocks
        json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_block_match:
            candidate = json_block_match.group(1).strip()
        else:
            # Look for outermost '{' and '}'
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = text[start : end + 1].strip()
            else:
                candidate = text

        try:
            parsed = json.loads(candidate)
            if not isinstance(parsed, dict):
                raise AIOutputInvalidException("Parsed AI response is not a valid JSON object/dictionary.")
            return parsed
        except json.JSONDecodeError as exc:
            raise AIOutputInvalidException(f"Failed to parse AI response as JSON: {exc}") from exc

    @classmethod
    def validate_schema(cls, raw_text: str, target_schema: Type[T]) -> T:
        """Parse raw text to JSON, then validate against a Pydantic schema."""
        data = cls.extract_json(raw_text)
        try:
            return target_schema.model_validate(data)
        except ValidationError as exc:
            raise AIOutputSchemaInvalidException(
                f"AI structured output failed schema validation for {target_schema.__name__}: {exc}"
            ) from exc
