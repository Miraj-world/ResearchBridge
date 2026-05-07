from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..config import settings
from ..schemas import Confidence, ProcessingState, UserLevel


HEADER_ROLE_MAP = {
    "abstract": "core_idea",
    "introduction": "problem",
    "background": "context",
    "related work": "context",
    "method": "implementation",
    "methods": "implementation",
    "methodology": "implementation",
    "approach": "implementation",
    "our approach": "implementation",
    "experiments": "validation",
    "evaluation": "validation",
    "results": "insights",
    "discussion": "insights",
    "conclusion": "summary",
}

ROLE_PRECEDENCE = [
    "implementation",
    "validation",
    "insights",
    "context",
    "problem",
    "core_idea",
    "summary",
]

TOOL_HINTS = {
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "huggingface": "HuggingFace",
    "jax": "JAX",
    "numpy": "NumPy",
    "scikit-learn": "scikit-learn",
}


@dataclass
class Chunk:
    chunk_id: str
    header: str
    text: str
    role: str


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_header(header: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", header.lower())).strip()


def chunk_markdown(markdown: str) -> list[tuple[str, str]]:
    lines = markdown.splitlines()
    chunks: list[tuple[str, str]] = []
    current_header = "Document"
    current_lines: list[str] = []

    for line in lines:
        header_match = re.match(r"^#{1,6}\s+(.*)$", line.strip())
        if header_match:
            if current_lines:
                chunks.append((current_header, "\n".join(current_lines).strip()))
                current_lines = []
            current_header = header_match.group(1).strip()
        else:
            current_lines.append(line)

    if current_lines:
        chunks.append((current_header, "\n".join(current_lines).strip()))

    if not chunks:
        chunks = [("Document", markdown)]

    cleaned = [(h, t) for h, t in chunks if t.strip()]
    return cleaned or [("Document", markdown.strip())]


def assign_role(header: str, text: str) -> tuple[str, Confidence]:
    normalized = _normalize_header(header)
    if normalized in HEADER_ROLE_MAP:
        return HEADER_ROLE_MAP[normalized], Confidence.high

    for key, role in HEADER_ROLE_MAP.items():
        if key in normalized:
            return role, Confidence.medium

    # Deterministic fallback based on lexical hints.
    lowered = f"{header}\n{text[:300]}".lower()
    guesses: list[str] = []
    if any(token in lowered for token in ("experiment", "benchmark", "dataset")):
        guesses.append("validation")
    if any(token in lowered for token in ("result", "accuracy", "f1", "bleu")):
        guesses.append("insights")
    if any(token in lowered for token in ("method", "pipeline", "architecture", "algorithm")):
        guesses.append("implementation")
    if any(token in lowered for token in ("motivation", "problem", "challenge")):
        guesses.append("problem")
    if any(token in lowered for token in ("summary", "conclusion")):
        guesses.append("summary")

    if guesses:
        for role in ROLE_PRECEDENCE:
            if role in guesses:
                return role, Confidence.low
    return "context", Confidence.low


def _simple_sentences(text: str, max_count: int = 3) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    return [p.strip() for p in parts if p.strip()][:max_count]


def _build_chunks(markdown: str) -> tuple[list[Chunk], list[dict[str, Any]]]:
    section_pairs = chunk_markdown(markdown)
    chunks: list[Chunk] = []
    low_conf_events: list[dict[str, Any]] = []
    for idx, (header, text) in enumerate(section_pairs, start=1):
        role, conf = assign_role(header, text)
        chunk_id = f"chunk_{idx}"
        chunks.append(Chunk(chunk_id=chunk_id, header=header, text=text, role=role))
        if conf == Confidence.low:
            low_conf_events.append(
                {
                    "event_time": _utc_iso(),
                    "stage": "tagged",
                    "event_type": "role_tag_low_confidence",
                    "event_payload": {"chunk_id": chunk_id, "header": header, "role": role},
                }
            )
    return chunks, low_conf_events


def _extract_tools(full_text: str) -> list[str]:
    low = full_text.lower()
    found: list[str] = []
    for token, normalized in TOOL_HINTS.items():
        if token in low:
            found.append(normalized)
    return sorted(set(found))


def _verify_sentence_support(sentence: str, source_text: str) -> tuple[bool, Confidence]:
    clean = re.sub(r"[^a-z0-9\s]", " ", sentence.lower())
    terms = [t for t in clean.split() if len(t) > 3]
    if not terms:
        return True, Confidence.medium
    overlap = sum(1 for t in terms if t in source_text.lower())
    ratio = overlap / max(len(terms), 1)
    if ratio >= 0.7:
        return True, Confidence.high
    if ratio >= 0.4:
        return True, Confidence.medium
    return False, Confidence.low


def _level_note(level: UserLevel) -> str:
    if level == UserLevel.beginner:
        return "Focus on intuition and execution order."
    if level == UserLevel.intermediate:
        return "Focus on conceptual mechanics and component interactions."
    return "Focus on design trade-offs and assumptions."


def adapt_text(text: str, level: UserLevel) -> str:
    # Adaptation is rewrite-only; does not add new claims.
    if level == UserLevel.beginner:
        return f"In simple terms: {text}"
    if level == UserLevel.intermediate:
        return f"Conceptually: {text}"
    return f"Technical view: {text}"


def process_markdown_to_document(
    *,
    paper_id: str,
    title: str,
    source_file: str,
    markdown: str,
    user_level: UserLevel,
    parser_path: str,
    existing_audit: list[dict[str, Any]] | None = None,
    timings_seed: dict[str, int] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    start = time.perf_counter()
    timings: dict[str, int] = dict(timings_seed or {})
    audit = list(existing_audit or [])

    t_chunk = time.perf_counter()
    chunks, low_conf_events = _build_chunks(markdown)
    timings["chunked"] = int((time.perf_counter() - t_chunk) * 1000)
    audit.extend(low_conf_events)

    role_groups: dict[str, list[Chunk]] = {}
    for c in chunks:
        role_groups.setdefault(c.role, []).append(c)

    t_extract = time.perf_counter()
    abstract_chunk = (role_groups.get("core_idea") or role_groups.get("problem") or chunks[:1])[0]
    problem_chunk = (role_groups.get("problem") or role_groups.get("context") or chunks[:1])[0]
    impl_chunks = role_groups.get("implementation") or chunks[:2]
    insight_chunks = role_groups.get("insights") or role_groups.get("validation") or chunks[-2:]

    core_sentences = _simple_sentences(abstract_chunk.text, max_count=2)
    problem_sentences = _simple_sentences(problem_chunk.text, max_count=2)
    step_sentences: list[tuple[str, str]] = []
    for c in impl_chunks[:4]:
        for s in _simple_sentences(c.text, max_count=2):
            step_sentences.append((c.chunk_id, s))
    step_sentences = step_sentences[:6]

    if not step_sentences:
        step_sentences = [(abstract_chunk.chunk_id, "Not specified in this paper section.")]

    timings["extracting"] = int((time.perf_counter() - t_extract) * 1000)

    t_verify = time.perf_counter()
    verified_steps: list[dict[str, Any]] = []
    suppressed_count = 0
    for idx, (chunk_id, sentence) in enumerate(step_sentences, start=1):
        src = next((c.text for c in chunks if c.chunk_id == chunk_id), "")
        supported, confidence = _verify_sentence_support(sentence, src)
        if not supported:
            suppressed_count += 1
            continue
        verified_steps.append(
            {
                "step": idx,
                "title": f"Step {idx}",
                "description": adapt_text(sentence, user_level),
                "level_notes": _level_note(user_level),
                "source_chunk_id": chunk_id,
                "confidence": confidence.value,
                "citations": [{"source_chunk_id": chunk_id}],
            }
        )

    if not verified_steps:
        fallback_chunk_id = abstract_chunk.chunk_id
        verified_steps.append(
            {
                "step": 1,
                "title": "Step 1",
                "description": "Not specified in this paper section.",
                "level_notes": _level_note(user_level),
                "source_chunk_id": fallback_chunk_id,
                "confidence": Confidence.low.value,
                "citations": [{"source_chunk_id": fallback_chunk_id}],
            }
        )

    timings["verifying"] = int((time.perf_counter() - t_verify) * 1000)

    all_text = "\n\n".join(c.text for c in chunks)
    detected_tools = _extract_tools(all_text)

    all_citations = [{"source_chunk_id": c.chunk_id} for c in chunks]
    architecture_nodes = ["Input", "Preprocessing", "Model", "Output"]
    architecture_sentence = _simple_sentences(
        " ".join([x for _, x in step_sentences]) or "Pipeline details are not fully specified.", max_count=1
    )[0]
    challenge_candidates = []
    for c in insight_chunks:
        for s in _simple_sentences(c.text, max_count=2):
            if any(token in s.lower() for token in ("limitation", "challenge", "future", "error", "failure")):
                challenge_candidates.append((c.chunk_id, s))
    if not challenge_candidates:
        challenge_candidates.append((problem_chunk.chunk_id, "Trade-offs are not explicitly detailed."))

    challenges = [
        {
            "challenge": adapt_text(s, user_level),
            "confidence": Confidence.medium.value,
            "citations": [{"source_chunk_id": cid}],
        }
        for cid, s in challenge_candidates[:3]
    ]

    core_summary = core_sentences[0] if core_sentences else "Core idea is not explicitly specified."
    core_intuition = core_sentences[1] if len(core_sentences) > 1 else core_summary
    prob_desc = problem_sentences[0] if problem_sentences else "Problem statement is not explicitly specified."
    prob_why = problem_sentences[1] if len(problem_sentences) > 1 else prob_desc

    t_adapt = time.perf_counter()
    document = {
        "schema_version": "1.1.0",
        "paper_id": paper_id,
        "title": title,
        "source_file": source_file,
        "processed_at": _utc_iso(),
        "user_level": user_level.value,
        "processing": {
            "state": ProcessingState.completed.value,
            "timings_ms": timings,
            "parser_path": parser_path,
            "last_error": None,
        },
        "core_idea": {
            "summary": adapt_text(core_summary, user_level),
            "intuition": adapt_text(core_intuition, user_level),
            "confidence": Confidence.high.value,
            "citations": [{"source_chunk_id": abstract_chunk.chunk_id}],
        },
        "problem": {
            "description": adapt_text(prob_desc, user_level),
            "why_it_matters": adapt_text(prob_why, user_level),
            "confidence": Confidence.high.value,
            "citations": [{"source_chunk_id": problem_chunk.chunk_id}],
        },
        "implementation": {
            "steps": verified_steps,
            "inputs_outputs": {"input": "Research problem and data assumptions", "output": "Validated model behavior"},
        },
        "architecture": {
            "pipeline": architecture_nodes,
            "description": adapt_text(architecture_sentence, user_level),
            "confidence": Confidence.medium.value,
            "citations": [{"source_chunk_id": verified_steps[0]["source_chunk_id"]}],
        },
        "tools": {
            "libraries": detected_tools or ["Not specified"],
            "frameworks": ["Not specified"],
            "notes": adapt_text("Tooling details are inferred from explicit mentions only.", user_level),
            "confidence": Confidence.medium.value,
            "citations": [{"source_chunk_id": abstract_chunk.chunk_id}],
        },
        "challenges": challenges,
        "analogy": "Think of the paper as a blueprint: sections describe intent, method, and evidence.",
        "comparison_ready": True,
        "citations": all_citations,
        "audit": audit,
    }
    timings["adapted"] = int((time.perf_counter() - t_adapt) * 1000)
    timings["total"] = int((time.perf_counter() - start) * 1000)
    document["processing"]["timings_ms"] = timings

    internal = {
        "markdown": markdown,
        "chunks": [c.__dict__ for c in chunks],
        "suppressed_unsupported_claims": suppressed_count,
        "verified_step_count": len(verified_steps),
    }
    return document, internal


def grounded_chat_answer(paper: dict[str, Any], question: str, level: UserLevel) -> dict[str, Any]:
    q = question.lower()
    answer = ""
    citations: list[dict[str, str]] = []
    confidence = Confidence.medium.value

    if "implement" in q or "build" in q or "steps" in q:
        steps = paper.get("implementation", {}).get("steps", [])
        if steps:
            lines = [s.get("description", "") for s in steps[:3]]
            answer = " ".join(lines)
            citations = [{"source_chunk_id": s.get("source_chunk_id", "")} for s in steps[:3]]
            confidence = Confidence.high.value
    elif "problem" in q or "why" in q:
        p = paper.get("problem", {})
        answer = f"{p.get('description', '')} {p.get('why_it_matters', '')}".strip()
        citations = p.get("citations", [])
        confidence = p.get("confidence", Confidence.medium.value)
    elif "core" in q or "idea" in q or "summary" in q:
        c = paper.get("core_idea", {})
        answer = f"{c.get('summary', '')} {c.get('intuition', '')}".strip()
        citations = c.get("citations", [])
        confidence = c.get("confidence", Confidence.medium.value)
    else:
        answer = "Not specified in the uploaded paper."
        citations = []
        confidence = Confidence.low.value

    if level == UserLevel.beginner and answer and not answer.startswith("Not specified"):
        answer = f"In simple terms: {answer}"
    elif level == UserLevel.advanced and answer and not answer.startswith("Not specified"):
        answer = f"Technical view: {answer}"

    return {"answer": answer, "citations": citations, "confidence": confidence}


def compare_documents(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_steps = left.get("implementation", {}).get("steps", [])
    right_steps = right.get("implementation", {}).get("steps", [])
    similarities = []
    differences = []

    left_pipeline = left.get("architecture", {}).get("pipeline", [])
    right_pipeline = right.get("architecture", {}).get("pipeline", [])
    if left_pipeline and right_pipeline:
        common = [x for x in left_pipeline if x in right_pipeline]
        if common:
            similarities.append(f"Both papers share pipeline components: {', '.join(common)}.")
        if left_pipeline != right_pipeline:
            differences.append("Pipeline composition differs between the papers.")

    similarities.append(
        f"Both papers are processed with schema v{left.get('schema_version')} and confidence-anchored outputs."
    )
    differences.append(f"Implementation steps count: left={len(left_steps)}, right={len(right_steps)}.")

    implementation_delta = []
    for i in range(max(len(left_steps), len(right_steps))):
        l = left_steps[i]["description"] if i < len(left_steps) else "not_available"
        r = right_steps[i]["description"] if i < len(right_steps) else "not_available"
        implementation_delta.append(f"Step {i + 1}: left={l} | right={r}")

    confidence_summary = {
        "left_core_idea": left.get("core_idea", {}).get("confidence", "low"),
        "right_core_idea": right.get("core_idea", {}).get("confidence", "low"),
        "left_problem": left.get("problem", {}).get("confidence", "low"),
        "right_problem": right.get("problem", {}).get("confidence", "low"),
    }

    return {
        "left_paper_id": left["paper_id"],
        "right_paper_id": right["paper_id"],
        "similarities": similarities,
        "differences": differences,
        "implementation_delta": implementation_delta,
        "confidence_summary": confidence_summary,
    }


def maybe_json_dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True)
