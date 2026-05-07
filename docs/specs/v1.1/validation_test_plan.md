# Phase 1 v1.1 Validation Test Plan

Date: 2026-05-06  
Scope: Spec-level validation for Phase 1 execution readiness

## 1. Test Objectives

- Validate that contracts are deterministic, grounded, and operable.
- Validate that all frozen API surfaces can pass end-to-end acceptance.
- Validate that failure behavior is explicit and recoverable where intended.

## 2. Archetype Validation Suite (Required)

### Case A1: Clean digital PDF
- Input: standard machine-readable academic PDF with clear headings.
- Expected:
- Docling-only path, no OCR.
- Role tagging from header mapping only.
- Completed state with no low-confidence flood.

### Case A2: Scanned PDF
- Input: image-based scanned paper.
- Expected:
- Docling fails threshold and OCR fallback triggers.
- OCR extraction succeeds or emits terminal parser failure with clear error payload.

### Case A3: Non-standard headings
- Input: paper using custom headings such as "Our Framework" and "Empirical Study."
- Expected:
- Fallback classifier invoked only for unmatched headings.
- Deterministic tie-breakers applied where ambiguity exists.

### Case A4: Table-heavy paper
- Input: paper with dense tables and multi-column layouts.
- Expected:
- Chunking preserves section-level structure.
- Claims linked to chunk anchors that include table-derived statements.

### Case A5: Missing method details
- Input: paper with vague implementation section.
- Expected:
- Extractor emits `not_specified` for absent details.
- Verifier suppresses unsupported claims.

### Case A6: Multi-column + figure-heavy layout
- Input: two-column paper with many figures and captions.
- Expected:
- Parsing remains stable.
- No ungrounded architectural claims from figure captions alone.

## 3. Determinism and Hallucination Controls

### D1: Repeated run determinism
- Run the same paper 5 times.
- Assert:
- Stable section keys and role assignment.
- Step ordering remains unchanged.
- Confidence variance stays within allowed tolerance (high/medium/low distribution drift <= 5%).

### D2: Adversarial unsupported claims
- Seed chunks with distractor language and ambiguous phrasing.
- Assert:
- Unsupported claims are marked low + inferred.
- Unsupported claims are excluded from main structured output.

### D3: Adaptation guardrail
- Re-run adaptation across all levels from same verified base.
- Assert:
- No new entities, numbers, components, or steps appear.
- Every adapted statement maps to verified claim IDs.

## 4. API Acceptance Tests (E2E)

### E1: Upload -> Process -> Status -> Get paper
- Validate envelope shape (`ok`, `data`, `error`, `request_id`) at each endpoint.
- Validate state transition sequence correctness.

### E2: Chat grounding
- Ask questions:
- directly answerable by source
- partially answerable
- unanswerable
- Assert:
- Anchors exist for factual statements.
- Unanswerable returns "Not specified in the uploaded paper."

### E3: Compare
- Compare two completed papers.
- Assert:
- Canonical section alignment.
- Missing fields represented as `not_available`.
- Confidence summaries present and per-side citations isolated.

### E4: Reprocess level
- Reprocess a completed paper to a new level.
- Assert:
- Parsing/extraction/verifier artifacts are reused.
- Adapted output updates while source claim grounding remains intact.

## 5. Failure UX Contract Tests

### F1: Parser fail
- Force Docling and OCR failure.
- Expect `PARSER_FAILED`, `stage=parsing`, `recoverable=false`, actionable `hint`.

### F2: Verifier timeout
- Simulate verifier timeout.
- Expect `VERIFICATION_FAILED`, `recoverable=true`, resumable from verify stage.

### F3: Partial-stage retry
- Fail in `extracting`, then retry.
- Expect no duplicate upload record and no stage rewind before extraction unless explicitly requested.

## 6. Exit Criteria

All of the following must pass before implementation sign-off:

1. Six archetype cases pass expected outcomes.
2. Determinism and hallucination control tests pass.
3. E2E contract tests pass for all 7 endpoints.
4. Failure UX payloads match documented error contract.
5. Persisted documents validate against `processed_paper.schema.json`.
