from __future__ import annotations

from backend.models.schemas import Confidence, ExtractedClaim, VerificationFlag, VerifiedClaim
from backend.pipeline.llm_client import AnthropicJSONClient, LLMClientError


SYSTEM_PROMPT = "You are a fact-checking assistant. You will be given a source text and a claim made about it. Verify if the claim is grounded in the source text."


def _normalize_confidence(value: str) -> Confidence:
    lowered = value.lower().strip()
    if lowered in {"high", "medium", "low"}:
        return Confidence(lowered)
    return Confidence.low


def _normalize_flag(value: str) -> VerificationFlag:
    lowered = value.lower().strip()
    if lowered in {"grounded", "inferred", "unsupported"}:
        return VerificationFlag(lowered)
    return VerificationFlag.unsupported


def verify_claims(
    extracted_claims: list[ExtractedClaim],
    chunk_map: dict[str, str],
    llm_client: AnthropicJSONClient,
    verifier_model: str,
) -> list[VerifiedClaim]:
    verified_claims: list[VerifiedClaim] = []

    for claim in extracted_claims:
        source_text = chunk_map.get(claim.source_chunk_id, "")
        user_prompt = (
            f"Source text: {source_text}\n"
            f"Claim: {claim.claim}\n\n"
            "Return JSON:\n"
            "{\n"
            '  "verified": true | false,\n'
            '  "confidence": "high | medium | low",\n'
            '  "flag": "grounded | inferred | unsupported",\n'
            '  "note": "string"\n'
            "}"
        )

        try:
            payload = llm_client.call_json(
                model=verifier_model,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=260,
                temperature=0.0,
            )
        except LLMClientError:
            payload = {
                "verified": False,
                "confidence": "low",
                "flag": "unsupported",
                "note": "Verifier failed to parse output for this claim.",
            }

        flag = _normalize_flag(str(payload.get("flag", "unsupported")))
        confidence = _normalize_confidence(str(payload.get("confidence", "low")))
        note = str(payload.get("note", "")).strip()

        if flag == VerificationFlag.unsupported:
            confidence = Confidence.low

        verified_claims.append(
            VerifiedClaim(
                claim=claim.claim,
                source_chunk_id=claim.source_chunk_id,
                raw_explanation=claim.raw_explanation,
                confidence=confidence,
                flag=flag,
                note=note,
            )
        )

    return verified_claims
