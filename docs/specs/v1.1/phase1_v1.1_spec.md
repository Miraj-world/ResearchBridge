# AI Research Paper Learning and Implementation Explainer
## Phase 1 Specification v1.1 (Execution-Risk Hardened)

Version: 1.1  
Date: 2026-05-06  
Status: Implementation Ready  
Defaults: OpenAI-first, Docling-primary, local MongoDB required

## 1. Summary

This v1.1 spec hardens the v1.0 report into a delivery-safe implementation contract.

- Introduces a risk-ranked critique with prioritized mitigations.
- Freezes backend APIs and canonical persisted schema.
- Defines deterministic parser and processing state transitions.
- Prevents ungrounded model output by policy at extraction, verification, adaptation, and chat layers.
- Adds testability and observability requirements so Phase 1 can be shipped and operated locally with predictable behavior.

## 2. Risk-Ranked Critique

### P0 (Ship Blockers)

1. Ambiguous processing state model
- Risk: Retries and failure handling become inconsistent across UI and backend.
- Mitigation: Enforce explicit state machine (`uploaded`, `parsing`, `parsed`, `chunked`, `tagged`, `extracting`, `verifying`, `aggregated`, `adapted`, `completed`, `failed`).

2. Unfrozen API contract
- Risk: Frontend and backend drift; phase integration breaks.
- Mitigation: Freeze OpenAPI endpoints and response envelopes in this release.

3. No canonical persisted schema with versioning
- Risk: Reprocessing and comparison fail when shape changes.
- Mitigation: Use one schema with `schema_version` and strict confidence enums.

4. Claim generation can exceed source evidence
- Risk: Hallucinated implementation steps shown as facts.
- Mitigation: Require claim-level source anchors and verifier suppression policy for unsupported claims.

### P1 (High Operational Risk)

1. Non-deterministic role tagging for unusual headers
- Risk: Same paper receives different output structures across runs.
- Mitigation: Header mapping precedence, deterministic tie-breakers, and fallback classifier constraints.

2. Level adaptation may introduce new claims
- Risk: Rewriter invents details not present in extracted facts.
- Mitigation: Adaptation is rewrite-only over verified claims; no new entities, numbers, or steps allowed.

3. Chat may free-generate beyond stored context
- Risk: Answers appear authoritative but ungrounded.
- Mitigation: Restrict retrieval to stored chunks and structured JSON, with "not found in source" fallback.

### P2 (Medium Risk)

1. Compare view mismatch across missing sections
- Risk: User confusion during side-by-side interpretation.
- Mitigation: Field alignment contract with explicit `not_available` placeholders.

2. Weak observability at stage boundaries
- Risk: Debugging parser/verifier failures becomes manual and slow.
- Mitigation: Per-stage metrics and per-paper audit event log required.

## 3. Frozen Phase 1 API Contract

All responses use:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "request_id": "uuid"
}
```

On failure:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "PARSER_FAILED",
    "message": "Docling and OCR extraction failed",
    "details": {}
  },
  "request_id": "uuid"
}
```

Required endpoints:

1. `POST /api/v1/upload`
- Input: multipart PDF file.
- Output: `paper_id`, `source_file`, initial `status=uploaded`.

2. `POST /api/v1/process`
- Input: `paper_id`, `user_level`.
- Behavior: starts pipeline or retries from allowed failure checkpoint.
- Output: accepted job token and current state.

3. `GET /api/v1/status/{paper_id}`
- Output: current pipeline state, progress summary, last_error if any.

4. `GET /api/v1/papers/{paper_id}`
- Output: stored structured paper JSON document.

5. `POST /api/v1/chat`
- Input: `paper_id`, `question`, optional `user_level`.
- Output: grounded answer with citation anchors and confidence summary.

6. `POST /api/v1/compare`
- Input: `left_paper_id`, `right_paper_id`, `user_level`.
- Output: aligned side-by-side comparison payload.

7. `POST /api/v1/reprocess-level`
- Input: `paper_id`, `target_user_level`.
- Behavior: reuse parsed and verified intermediate data; rerun adaptation only.
- Output: updated level-specific view and timestamps.

## 4. Canonical Persisted Schema Rules

Collection: `processed_papers`  
Schema file: `processed_paper.schema.json`

Required top-level fields:

- `schema_version` (fixed to `1.1.0`)
- `paper_id` (UUID)
- `title`
- `source_file`
- `processed_at` (ISO-8601 UTC)
- `user_level` (`beginner|intermediate|advanced`)
- `processing`
- `core_idea`
- `problem`
- `implementation`
- `architecture`
- `tools`
- `challenges`
- `comparison_ready`
- `citations`
- `audit`

Confidence enum:

- `high`: directly supported by source text
- `medium`: partially supported or compressed from multiple supported claims
- `low`: inferred content, must be flagged in UI

Citation anchor requirements:

- Every user-visible claim in `core_idea`, `problem`, `implementation.steps`, `architecture`, `tools`, and `challenges` must include at least one `source_chunk_id`.
- Missing anchor is a validation failure unless the field value is explicitly `not_specified`.

## 5. Deterministic Parser and Processing State Machine

### 5.1 State Flow

`uploaded -> parsing -> parsed -> chunked -> tagged -> extracting -> verifying -> aggregated -> adapted -> completed`

Failure state:

- Any stage can transition to `failed` with stage-scoped error metadata.

### 5.2 Docling and OCR Policy

1. Run Docling first.
2. If Docling returns usable markdown above extraction threshold, continue.
3. Trigger OCR fallback only when one of these is true:
- Docling throws fatal parse exception.
- Output text density below configured minimum.
- Structural extraction missing all markdown headings.
4. OCR runs at 300 DPI via pytesseract.
5. If OCR also fails threshold checks, emit terminal `PARSER_FAILED`.

### 5.3 Error Payload Contract

`error.code` must be one of:

- `UPLOAD_INVALID_FILE`
- `PARSER_FAILED`
- `OCR_FAILED`
- `CHUNKING_FAILED`
- `ROLE_TAGGING_FAILED`
- `EXTRACTION_FAILED`
- `VERIFICATION_FAILED`
- `ADAPTATION_FAILED`
- `NOT_FOUND`
- `BAD_REQUEST`
- `INTERNAL_ERROR`

`error.details` must include:

- `stage`
- `recoverable` (boolean)
- `hint` (human-readable next action)

## 6. Role Tagging Contract

Resolution order:

1. Exact header dictionary match (case-insensitive).
2. Normalized header synonym match.
3. LLM fallback classifier on first 100 section words.
4. Deterministic tie-break by precedence:
- `implementation > validation > insights > context > problem > core_idea > summary`

If classifier confidence is below threshold:

- Assign `context` and mark confidence `low`.
- Add audit event `role_tag_low_confidence`.

## 7. Dual-LLM Verification Policy

Extractor (LLM 1) requirements:

- Emit atomic claims only (one technical assertion per claim object).
- Include `source_chunk_id` on every claim.
- Use `not_specified` instead of inferred details.

Verifier (LLM 2) requirements:

- Evaluate each claim against original chunk text.
- Set `support_status`:
- `supported`
- `partially_supported`
- `unsupported`
- Map support to confidence:
- `supported -> high`
- `partially_supported -> medium`
- `unsupported -> low` and `inferred=true`

Suppression rule:

- Claims marked `unsupported` are excluded from core structured output unless user explicitly requests inferred hypotheses in chat.

## 8. Level Adaptation Boundaries

Adaptation may change:

- Vocabulary complexity
- Explanation density
- Presence of analogies

Adaptation may not change:

- Numerical values
- Architecture components
- Step count or sequence
- Claim polarity
- Tools or frameworks named in verified output

Validation gate:

- Post-adaptation diff checker ensures every adapted claim maps to a verified source claim ID.
- Any unmatched claim fails adaptation stage.

## 9. Chat Grounding Policy

Chat retrieval sources:

1. Persisted structured JSON sections.
2. Original stored chunk text linked by `source_chunk_id`.

Response policy:

- Every factual statement must cite chunk anchor(s).
- If answer is not derivable from sources, return:
- `answer`: "Not specified in the uploaded paper."
- `confidence`: `low`
- `citations`: `[]`

Disallowed in Phase 1:

- External web retrieval
- Cross-paper synthesis in single-paper chat endpoint
- Code generation from paper implementation sections

## 10. Compare Contract

Input: two existing `paper_id`s and `user_level`.

Alignment rules:

1. Align by canonical section keys:
- `core_idea`, `problem`, `implementation`, `architecture`, `tools`, `challenges`
2. For missing fields, set value to `not_available` with confidence `low`.
3. Keep each side's citations isolated; never merge anchors.
4. Show confidence side-by-side per field and per implementation step.

Comparison output includes:

- `similarities`
- `differences`
- `implementation_delta`
- `confidence_summary`

All statements must be grounded to left or right source anchors.

## 11. Observability Minimums

Required per-paper metrics:

- Stage durations (ms) for all pipeline stages
- Parser fallback indicator (`docling_only`, `docling_plus_ocr`, `ocr_only`)
- Claim counts (`generated`, `verified_supported`, `suppressed_unsupported`)
- Chat grounding ratio (`anchored_statements / total_statements`)

Required counters:

- `parser_failures_total`
- `ocr_failures_total`
- `verification_failures_total`
- `adaptation_failures_total`

Audit trail fields:

- `event_time`
- `paper_id`
- `stage`
- `event_type`
- `event_payload`

Retention:

- Keep local audit trail for minimum 30 days in Phase 1.

## 12. Phase 1 Acceptance Criteria

Phase 1 is ready when:

1. All required endpoints are implemented against frozen schemas.
2. The 6 archetype validation suite passes.
3. Repeated runs on same paper preserve structure and role assignment deterministically.
4. Unsupported claims are suppressed from primary output.
5. Chat answers remain grounded or explicitly return "not specified."
