"""Version-controlled prompts repository for HealthSetu AI tasks (Phase 14).

All prompts enforce:
1. Strict separation of System Instructions, Task Directives, and Untrusted Clinical Sources.
2. Explicit boundary delimiters around source text to prevent prompt injection.
3. Structured output requirements adhering to Pydantic models.
4. Grounding and source citation instructions.
5. Explicit clinical negative constraints (no autonomous diagnosing, prescribing, or triage).
"""

from app.schemas.ai import AITaskType

PROMPT_BUNDLE_VERSION = "1.0.0"
