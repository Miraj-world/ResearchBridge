from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel


class UserLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class VerificationFlag(str, Enum):
    grounded = "grounded"
    inferred = "inferred"
    unsupported = "unsupported"


class SectionRole(str, Enum):
    core_idea = "core_idea"
    problem = "problem"
    context = "context"
    implementation = "implementation"
    validation = "validation"
    insights = "insights"
    summary = "summary"


class ProcessingStage(str, Enum):
    parsing = "parsing"
    chunking = "chunking"
    extracting = "extracting"
    verifying = "verifying"
    aggregation = "aggregation"
    adaptation = "adaptation"
    done = "done"


class ErrorInfo(BaseModel):
    code: str
    message: str


T = TypeVar("T")


class ApiEnvelope(GenericModel, Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None


class ChunkModel(BaseModel):
    chunk_id: str
    header: str
    role: SectionRole
    text: str
    section_index: int


class ExtractedClaim(BaseModel):
    claim: str
    source_chunk_id: str
    confidence: Confidence
    raw_explanation: str


class VerifiedClaim(BaseModel):
    claim: str
    source_chunk_id: str
    raw_explanation: str
    confidence: Confidence
    flag: VerificationFlag
    note: str


class CoreIdea(BaseModel):
    summary: str
    intuition: str
    confidence: Confidence


class Problem(BaseModel):
    description: str
    why_it_matters: str
    confidence: Confidence


class ImplementationStep(BaseModel):
    step: int
    title: str
    description: str
    level_notes: str
    source_chunk_id: str
    confidence: Confidence


class InputsOutputs(BaseModel):
    input: str
    output: str
    confidence: Confidence


class Implementation(BaseModel):
    steps: list[ImplementationStep]
    inputs_outputs: InputsOutputs


class Architecture(BaseModel):
    pipeline: list[str]
    description: str
    confidence: Confidence


class Tools(BaseModel):
    libraries: list[str]
    frameworks: list[str]
    notes: str
    confidence: Confidence


class Challenge(BaseModel):
    challenge: str
    confidence: Confidence


class ProcessedPaper(BaseModel):
    paper_id: UUID
    title: str
    source_file: str
    processed_at: str
    user_level: UserLevel
    core_idea: CoreIdea
    problem: Problem
    implementation: Implementation
    architecture: Architecture
    tools: Tools
    challenges: list[Challenge]
    analogy: str
    analogy_confidence: Confidence
    comparison_ready: Literal[True] = True
    chunks: list[ChunkModel]
    stage_history: list[ProcessingStage] = Field(default_factory=list)


class UploadResponse(BaseModel):
    paper_id: UUID
    title: str
    processed_at: str
    stage_history: list[ProcessingStage]


class PaperListItem(BaseModel):
    paper_id: UUID
    title: str
    processed_at: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    paper_id: UUID
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    referenced_sections: list[str]
    confidence: Confidence


class CompareRequest(BaseModel):
    paper_id_1: UUID
    paper_id_2: UUID


class CompareResponse(BaseModel):
    paper_1: ProcessedPaper
    paper_2: ProcessedPaper


class JobRecord(BaseModel):
    paper_id: UUID
    source_file: str
    title: str
    user_level: UserLevel
    status: ProcessingStage
    stage_history: list[ProcessingStage] = Field(default_factory=list)
    markdown: str = ""
    chunks: list[ChunkModel] = Field(default_factory=list)
    created_at: str


class UploadJobResult(BaseModel):
    paper_id: UUID
    file_path: str
    file_name: str
    title: str
    user_level: UserLevel


class IngestionResult(BaseModel):
    markdown: str
    parser_used: str


class SectionChunk(BaseModel):
    chunk_id: str
    header: str
    text: str
    section_index: int


class ChunkWithRole(BaseModel):
    chunk_id: str
    header: str
    text: str
    section_index: int
    role: SectionRole


class AggregationInput(BaseModel):
    paper_id: UUID
    title: str
    source_file: str
    user_level: UserLevel
    chunks: list[ChunkWithRole]
    verified_claims: list[VerifiedClaim]


class StorageWriteResult(BaseModel):
    stored_in: Literal["mongodb", "json"]
    path: str | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
