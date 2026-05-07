from __future__ import annotations

import re

from backend.models.schemas import ChunkWithRole, SectionChunk, SectionRole
from backend.pipeline.llm_client import AnthropicJSONClient, LLMClientError

_HEADER_ROLE_MAP: dict[str, SectionRole] = {
    "abstract": SectionRole.core_idea,
    "introduction": SectionRole.problem,
    "related work": SectionRole.context,
    "methodology": SectionRole.implementation,
    "method": SectionRole.implementation,
    "our approach": SectionRole.implementation,
    "the framework": SectionRole.implementation,
    "experiments": SectionRole.validation,
    "experimental setup": SectionRole.validation,
    "results": SectionRole.insights,
    "findings": SectionRole.insights,
    "conclusion": SectionRole.summary,
    "discussion": SectionRole.summary,
}


def _normalize_header(header: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", header.lower())).strip()


def _match_role_from_header(header: str) -> SectionRole | None:
    normalized = _normalize_header(header)
    for key, role in _HEADER_ROLE_MAP.items():
        if normalized == key or key in normalized:
            return role
    return None


def _classify_role_with_llm(llm_client: AnthropicJSONClient, model: str, chunk: SectionChunk) -> SectionRole:
    first_100_words = " ".join(chunk.text.split()[:100])
    system_prompt = "You are a research paper classifier."
    user_prompt = (
        "What role does this section play? First 100 words: "
        f"{first_100_words}. "
        "Choose exactly one: core_idea / problem / context / implementation / validation / insights / summary. "
        "Reply with the label only."
    )
    label = llm_client.call_text(
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=24,
        temperature=0.0,
    ).strip().lower()
    try:
        return SectionRole(label)
    except Exception as exc:
        raise LLMClientError(f"Invalid role label from classifier: {label}") from exc


def assign_roles(chunks: list[SectionChunk], llm_client: AnthropicJSONClient, classifier_model: str) -> list[ChunkWithRole]:
    assigned: list[ChunkWithRole] = []
    for chunk in chunks:
        mapped_role = _match_role_from_header(chunk.header)
        role = mapped_role
        if role is None:
            try:
                role = _classify_role_with_llm(llm_client, classifier_model, chunk)
            except Exception:
                role = SectionRole.context

        assigned.append(
            ChunkWithRole(
                chunk_id=chunk.chunk_id,
                header=chunk.header,
                text=chunk.text,
                section_index=chunk.section_index,
                role=role,
            )
        )
    return assigned
