from __future__ import annotations

from backend.models.schemas import ChunkWithRole, Confidence, ExtractedClaim
from backend.pipeline.llm_client import AnthropicJSONClient, LLMClientError


SYSTEM_PROMPT = """You are an expert AI/ML research explainer. You will be given a section of a research paper. Your job is to extract structured information from it.

STRICT RULES:
- Only explain what is EXPLICITLY stated in the provided text
- Do NOT infer, assume, or add external knowledge
- For every claim, include the source_chunk_id
- If something is unclear or not mentioned, write: 'Not specified in this section'
- Output valid JSON only. No preamble, no markdown fences."""


def _normalize_confidence(value: str) -> Confidence:
    lowered = value.lower().strip()
    if lowered in {"high", "medium", "low"}:
        return Confidence(lowered)
    return Confidence.low


def extract_claims(
    chunks: list[ChunkWithRole],
    llm_client: AnthropicJSONClient,
    extractor_model: str,
) -> tuple[list[ExtractedClaim], list[str]]:
    extracted: list[ExtractedClaim] = []
    skipped_chunk_ids: list[str] = []

    for chunk in chunks:
        user_prompt = (
            f"Section role: {chunk.role.value}\n"
            f"Chunk ID: {chunk.chunk_id}\n"
            f"Text: {chunk.text}\n\n"
            "Return JSON with these fields:\n"
            "{\n"
            '  "claim": "string",\n'
            '  "source_chunk_id": "string",\n'
            '  "confidence": "high | medium | low",\n'
            '  "raw_explanation": "string"\n'
            "}"
        )

        try:
            payload = llm_client.call_json(
                model=extractor_model,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=700,
                temperature=0.0,
            )
        except LLMClientError:
            skipped_chunk_ids.append(chunk.chunk_id)
            continue

        claim = str(payload.get("claim", "Not specified in this section")).strip() or "Not specified in this section"
        source_chunk_id = str(payload.get("source_chunk_id", chunk.chunk_id)).strip() or chunk.chunk_id
        raw_explanation = (
            str(payload.get("raw_explanation", "Not specified in this section")).strip() or "Not specified in this section"
        )
        confidence = _normalize_confidence(str(payload.get("confidence", "low")))

        extracted.append(
            ExtractedClaim(
                claim=claim,
                source_chunk_id=source_chunk_id,
                confidence=confidence,
                raw_explanation=raw_explanation,
            )
        )

    return extracted, skipped_chunk_ids
