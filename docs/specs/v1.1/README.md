# ResearchBridge Phase 1 Spec v1.1

This folder contains the decision-complete Phase 1 hardening specification.

- `phase1_v1.1_spec.md`: Execution-risk critique, deterministic behavior rules, and operating policies.
- `openapi.yaml`: Frozen backend API contract for Phase 1.
- `processed_paper.schema.json`: Canonical persisted document schema for `processed_papers`.
- `validation_test_plan.md`: Spec validation and acceptance test matrix.

Locked defaults for v1.1:

- OpenAI-first LLM provider
- Docling as primary parser
- Local MongoDB required
