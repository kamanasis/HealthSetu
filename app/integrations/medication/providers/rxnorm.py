"""RxNorm terminology provider adapter for standardizing medication concepts."""

import asyncio
from typing import Any
import httpx

from app.core.logging import get_logger
from app.integrations.medication.base import (
    MedicationTerminologyProvider,
    NormalizedConcept,
    RawMedicationInput,
    TerminologyLookupResult,
)
from app.integrations.medication.providers.local import (
    normalize_dosage_form,
    normalize_route,
    normalize_strength,
)
from app.schemas.prescription import NormalizationStatus

logger = get_logger("rxnorm_provider")

DEFAULT_RXNORM_BASE_URL = "https://rxnav.nlm.nih.gov/REST"
PROVIDER_NAME = "rxnorm"
PROVIDER_VERSION = "2026-nlm-rest"


class RxNormProvider:
    """Terminology provider adapter integrating NIH National Library of Medicine RxNorm REST API.

    CRITICAL ARCHITECTURAL BOUNDARY:
    RxNorm is used strictly for terminology concept standardization (RxCUI mapping).
    It is NOT a medication-safety engine and DOES NOT perform allergy checking, drug-drug interaction
    checking, or dosing verification.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int = 10,
        max_retries: int = 2,
    ) -> None:
        self.base_url = (base_url or DEFAULT_RXNORM_BASE_URL).rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def normalize(self, medication_input: RawMedicationInput) -> TerminologyLookupResult:
        """Query RxNorm REST API to obtain RxCUI and canonical medication representation."""
        raw_name = medication_input.drug_name_raw.strip()
        url = f"{self.base_url}/rxcui.json"
        params = {"name": raw_name, "search": 1}

        headers: dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        attempt = 0
        last_error: str | None = None

        while attempt <= self.max_retries:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(url, params=params, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        return self._parse_rxnorm_response(data, medication_input)
                    elif response.status_code == 404:
                        return TerminologyLookupResult(
                            status=NormalizationStatus.UNMATCHED,
                            error_message=f"RxNorm returned no matches for '{raw_name}'.",
                        )
                    elif response.status_code >= 500:
                        last_error = f"RxNorm service error: HTTP {response.status_code}"
                        logger.warning(f"Transient RxNorm HTTP {response.status_code} on attempt {attempt}")
                        if attempt <= self.max_retries:
                            await asyncio.sleep(0.5 * attempt)
                            continue
                    else:
                        return TerminologyLookupResult(
                            status=NormalizationStatus.FAILED,
                            error_code="TERMINOLOGY_PROVIDER_ERROR",
                            error_message=f"RxNorm request failed with HTTP {response.status_code}",
                        )
            except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                last_error = "RxNorm connection timed out"
                logger.warning(f"RxNorm timeout on attempt {attempt}: {e}")
                if attempt <= self.max_retries:
                    await asyncio.sleep(0.5 * attempt)
                    continue
                return TerminologyLookupResult(
                    status=NormalizationStatus.FAILED,
                    error_code="TERMINOLOGY_PROVIDER_TIMEOUT",
                    error_message="RxNorm terminology provider timed out after repeated attempts.",
                )
            except httpx.RequestError as e:
                last_error = f"RxNorm network request error: {str(e)}"
                logger.warning(f"RxNorm request error on attempt {attempt}: {e}")
                if attempt <= self.max_retries:
                    await asyncio.sleep(0.5 * attempt)
                    continue
                return TerminologyLookupResult(
                    status=NormalizationStatus.FAILED,
                    error_code="TERMINOLOGY_PROVIDER_UNAVAILABLE",
                    error_message="RxNorm service unavailable.",
                )

        return TerminologyLookupResult(
            status=NormalizationStatus.FAILED,
            error_code="TERMINOLOGY_PROVIDER_FAILED",
            error_message=last_error or "RxNorm request failed.",
        )

    def _parse_rxnorm_response(
        self, data: dict[str, Any], medication_input: RawMedicationInput
    ) -> TerminologyLookupResult:
        """Parse RxNorm JSON structure to identify single match or ambiguity."""
        id_group = data.get("idGroup", {})
        rxnorm_ids = id_group.get("rxnormId", [])

        if not rxnorm_ids:
            return TerminologyLookupResult(
                status=NormalizationStatus.UNMATCHED,
                error_message=f"No RxNorm CUI found for '{medication_input.drug_name_raw}'.",
            )

        if len(rxnorm_ids) > 1:
            # Multiple matches returned — do not guess!
            return TerminologyLookupResult(
                status=NormalizationStatus.AMBIGUOUS,
                potential_matches=[str(cui) for cui in rxnorm_ids[:5]],
                error_message=f"Multiple RxCUI candidates identified for '{medication_input.drug_name_raw}'.",
            )

        # Unique match
        rxcui = str(rxnorm_ids[0])
        name = id_group.get("name") or medication_input.drug_name_raw

        norm_strength = normalize_strength(medication_input.strength_raw)
        norm_form = normalize_dosage_form(medication_input.dosage_form_raw)
        norm_route = normalize_route(medication_input.route_raw)

        concept = NormalizedConcept(
            canonical_name=name,
            generic_name=name,
            brand_name=None,
            terminology_system="RXNORM",
            terminology_code=rxcui,
            normalized_strength=norm_strength,
            normalized_dosage_form=norm_form,
            normalized_route=norm_route,
            confidence_score=0.95,
            provider=PROVIDER_NAME,
            provider_version=PROVIDER_VERSION,
        )

        return TerminologyLookupResult(
            status=NormalizationStatus.MATCHED,
            concept=concept,
        )
