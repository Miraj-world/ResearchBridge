from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class UserLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class ProcessingState(str, Enum):
    uploaded = "uploaded"
    parsing = "parsing"
    parsed = "parsed"
    chunked = "chunked"
    tagged = "tagged"
    extracting = "extracting"
    verifying = "verifying"
    aggregated = "aggregated"
    adapted = "adapted"
    completed = "completed"
    failed = "failed"


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiResponse(BaseModel):
    ok: bool
    data: Any = None
    error: ApiError | None = None
    request_id: str


class ProcessRequest(BaseModel):
    paper_id: str
    user_level: UserLevel


class ChatRequest(BaseModel):
    paper_id: str
    question: str
    user_level: UserLevel | None = None


class CompareRequest(BaseModel):
    left_paper_id: str
    right_paper_id: str
    user_level: UserLevel


class ReprocessLevelRequest(BaseModel):
    paper_id: str
    target_user_level: UserLevel


class Citation(BaseModel):
    source_chunk_id: str


class ImplementationStep(BaseModel):
    step: int
    title: str
    description: str
    level_notes: str
    source_chunk_id: str
    confidence: Confidence
    citations: list[Citation]


class AnchoredText(BaseModel):
    summary: str
    intuition: str
    confidence: Confidence
    citations: list[Citation]


class ProblemField(BaseModel):
    description: str
    why_it_matters: str
    confidence: Confidence
    citations: list[Citation]


class ArchitectureField(BaseModel):
    pipeline: list[str]
    description: str
    confidence: Confidence
    citations: list[Citation]


class ToolsField(BaseModel):
    libraries: list[str]
    frameworks: list[str]
    notes: str
    confidence: Confidence
    citations: list[Citation]


class ChallengeField(BaseModel):
    challenge: str
    confidence: Confidence
    citations: list[Citation]


class ProcessingField(BaseModel):
    state: ProcessingState
    timings_ms: dict[str, int] = Field(default_factory=dict)
    parser_path: str | None = None
    last_error: dict[str, Any] | None = None


class ProcessedPaper(BaseModel):
    schema_version: str = "1.1.0"
    paper_id: str
    title: str
    source_file: str
    processed_at: str = Field(default_factory=utc_now_iso)
    user_level: UserLevel
    processing: ProcessingField
    core_idea: AnchoredText
    problem: ProblemField
    implementation: dict[str, Any]
    architecture: ArchitectureField
    tools: ToolsField
    challenges: list[ChallengeField]
    analogy: str
    comparison_ready: bool = True
    citations: list[Citation]
    audit: list[dict[str, Any]]


ERROR_CODES = {
    "UPLOAD_INVALID_FILE",
    "PARSER_FAILED",
    "OCR_FAILED",
    "CHUNKING_FAILED",
    "ROLE_TAGGING_FAILED",
    "EXTRACTION_FAILED",
    "VERIFICATION_FAILED",
    "ADAPTATION_FAILED",
    "NOT_FOUND",
    "BAD_REQUEST",
    "INTERNAL_ERROR",
}
