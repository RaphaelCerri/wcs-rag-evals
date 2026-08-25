"""Typed contracts for human annotation and calibrated LLM judging."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

HumanLabel = Literal["pass", "fail", "unsure"]
JudgeLabel = Literal["pass", "fail"]
ErrorFlag = Literal[
    "unsupported_claim",
    "irrelevant",
    "citation_mismatch",
    "material_omission",
    "unsafe_refusal",
    "language_mismatch",
]


class EvidencePassage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    chunk_id: str
    text: str = Field(min_length=1)
    cited: bool


class AnnotationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    case_id: str
    phase: Literal["calibration", "validation"]
    split: Literal["dev", "test"]
    language: Literal["en", "pt-BR"]
    category: str
    difficulty: str
    question: str
    answerable: bool
    answer: str
    citations: list[str]
    evidence: list[EvidencePassage]
    reference_answer: str
    required_facts: list[str]
    forbidden_claims: list[str]


class HumanAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    reviewer: str | None = None
    qualification: str | None = None
    label: HumanLabel | None = None
    error_flags: list[ErrorFlag] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def flags_require_fail_label(self) -> HumanAnnotation:
        if self.error_flags and self.label not in ("fail", "unsure"):
            raise ValueError("error flags require a fail or unsure label")
        if self.label is not None and (not self.reviewer or not self.qualification):
            raise ValueError("completed human labels require reviewer and qualification")
        if self.label == "unsure" and not self.notes.strip():
            raise ValueError("unsure labels require a note")
        return self


class ReviewerVote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["CEA", "CSA", "CFA-reviewer"]
    reviewer_type: Literal["model_assisted"] = "model_assisted"
    label: HumanLabel
    blinded_to_persisted_labels: bool


class ReferenceAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    case_id: str
    reference_type: Literal["model_assisted_adjudication"]
    label: HumanLabel
    error_flags: list[ErrorFlag] = Field(default_factory=list)
    rationale: str = Field(min_length=1)
    votes: list[ReviewerVote] = Field(min_length=2)

    @model_validator(mode="after")
    def consensus_must_be_unanimous_and_reviewed_blind(self) -> ReferenceAnnotation:
        if any(vote.label != self.label for vote in self.votes):
            raise ValueError("adjudicated reference requires unanimous votes")
        if sum(vote.blinded_to_persisted_labels for vote in self.votes) < 2:
            raise ValueError("at least two votes must be blind to persisted labels")
        if self.error_flags and self.label not in ("fail", "unsure"):
            raise ValueError("error flags require a fail or unsure label")
        if self.label == "unsure" and not self.rationale.strip():
            raise ValueError("unsure labels require a rationale")
        return self


class JudgeVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: JudgeLabel
    groundedness: int = Field(ge=0, le=2)
    relevance: int = Field(ge=0, le=2)
    citation_support: int = Field(ge=0, le=2)
    completeness: int = Field(ge=0, le=2)
    error_flags: list[ErrorFlag]
    rationale: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def label_matches_scores(self) -> JudgeVerdict:
        should_pass = (
            all(
                score == 2
                for score in (
                    self.groundedness,
                    self.relevance,
                    self.citation_support,
                    self.completeness,
                )
            )
            and not self.error_flags
        )
        if (self.label == "pass") != should_pass:
            raise ValueError("pass requires four scores of 2 and no error flags")
        return self
