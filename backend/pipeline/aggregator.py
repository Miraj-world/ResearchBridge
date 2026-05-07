from __future__ import annotations

from backend.models.schemas import (
    AggregationInput,
    Architecture,
    Challenge,
    ChunkModel,
    Confidence,
    CoreIdea,
    Implementation,
    ImplementationStep,
    InputsOutputs,
    Problem,
    ProcessedPaper,
    Tools,
    utc_now_iso,
)

_LIBRARY_HINTS = {
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "huggingface": "HuggingFace",
    "transformers": "Transformers",
    "jax": "JAX",
    "numpy": "NumPy",
    "scikit-learn": "scikit-learn",
}


def _best_confidence(confidences: list[Confidence]) -> Confidence:
    if not confidences:
        return Confidence.low
    if any(c == Confidence.low for c in confidences):
        return Confidence.low
    if any(c == Confidence.medium for c in confidences):
        return Confidence.medium
    return Confidence.high


def _first_or_default(values: list[str], default: str = "Not specified in this section") -> str:
    for value in values:
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return default


def aggregate_results(payload: AggregationInput) -> ProcessedPaper:
    claims_by_role: dict[str, list[tuple[str, Confidence, str]]] = {}
    role_lookup = {chunk.chunk_id: chunk.role.value for chunk in payload.chunks}

    for claim in payload.verified_claims:
        role = role_lookup.get(claim.source_chunk_id, "context")
        claims_by_role.setdefault(role, []).append((claim.claim, claim.confidence, claim.source_chunk_id))

    core_claims = claims_by_role.get("core_idea", [])
    problem_claims = claims_by_role.get("problem", [])
    impl_claims = claims_by_role.get("implementation", [])
    insight_claims = claims_by_role.get("insights", [])
    validation_claims = claims_by_role.get("validation", [])

    core_texts = [x[0] for x in core_claims]
    problem_texts = [x[0] for x in problem_claims]

    if not core_texts:
        core_texts = ["Not specified in this section"]
    if not problem_texts:
        problem_texts = ["Not specified in this section"]

    steps: list[ImplementationStep] = []
    for index, (claim_text, confidence, source_chunk_id) in enumerate(impl_claims[:8], start=1):
        steps.append(
            ImplementationStep(
                step=index,
                title=f"Step {index}",
                description=claim_text,
                level_notes="Not specified in this section",
                source_chunk_id=source_chunk_id,
                confidence=confidence,
            )
        )

    if not steps:
        steps.append(
            ImplementationStep(
                step=1,
                title="Step 1",
                description="Not specified in this section",
                level_notes="Not specified in this section",
                source_chunk_id=payload.chunks[0].chunk_id if payload.chunks else "section_1_part_1",
                confidence=Confidence.low,
            )
        )

    full_text = "\n".join(chunk.text for chunk in payload.chunks).lower()
    libraries = [name for key, name in _LIBRARY_HINTS.items() if key in full_text]

    challenges_source = insight_claims + validation_claims
    challenges: list[Challenge] = []
    for claim_text, confidence, _chunk_id in challenges_source[:5]:
        if any(term in claim_text.lower() for term in ["limit", "challenge", "error", "trade-off", "failure"]):
            challenges.append(Challenge(challenge=claim_text, confidence=confidence))

    if not challenges:
        challenges.append(Challenge(challenge="Not specified in this section", confidence=Confidence.low))

    architecture_pipeline = ["Input", "Preprocessing", "Model", "Output"]
    architecture_desc = _first_or_default([x[0] for x in impl_claims])

    return ProcessedPaper(
        paper_id=payload.paper_id,
        title=payload.title,
        source_file=payload.source_file,
        processed_at=utc_now_iso(),
        user_level=payload.user_level,
        core_idea=CoreIdea(
            summary=_first_or_default(core_texts),
            intuition=_first_or_default(core_texts[1:] if len(core_texts) > 1 else core_texts),
            confidence=_best_confidence([x[1] for x in core_claims]),
        ),
        problem=Problem(
            description=_first_or_default(problem_texts),
            why_it_matters=_first_or_default(problem_texts[1:] if len(problem_texts) > 1 else problem_texts),
            confidence=_best_confidence([x[1] for x in problem_claims]),
        ),
        implementation=Implementation(
            steps=steps,
            inputs_outputs=InputsOutputs(
                input="Not specified in this section",
                output="Not specified in this section",
                confidence=Confidence.low,
            ),
        ),
        architecture=Architecture(
            pipeline=architecture_pipeline,
            description=architecture_desc,
            confidence=_best_confidence([x[1] for x in impl_claims]),
        ),
        tools=Tools(
            libraries=libraries,
            frameworks=["Not specified in this section"],
            notes="Only explicitly mentioned tools are included.",
            confidence=Confidence.medium if libraries else Confidence.low,
        ),
        challenges=challenges,
        analogy="Not specified in this section",
        analogy_confidence=Confidence.low,
        comparison_ready=True,
        chunks=[
            ChunkModel(
                chunk_id=chunk.chunk_id,
                header=chunk.header,
                role=chunk.role,
                text=chunk.text,
                section_index=chunk.section_index,
            )
            for chunk in payload.chunks
        ],
        stage_history=[],
    )
