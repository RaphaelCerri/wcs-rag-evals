from __future__ import annotations

import pytest
from pydantic import ValidationError

from wcs_rag_evals.judge import cohens_kappa, exact_agreement, judge_payload, majority_label
from wcs_rag_evals.judge_contracts import AnnotationItem, EvidencePassage, JudgeVerdict


def _item() -> AnnotationItem:
    return AnnotationItem(
        case_id="wcs-dev-001",
        phase="calibration",
        split="dev",
        language="en",
        category="architecture",
        difficulty="basic",
        question="Where does the system sit in the architecture?",
        answerable=True,
        answer="Between upstream and equipment.",
        citations=["architecture.md"],
        evidence=[
            EvidencePassage(
                document_id="architecture.md",
                chunk_id="architecture.md::1",
                text="The WCS coordinates equipment work.",
                cited=True,
            )
        ],
        reference_answer="It coordinates equipment work.",
        required_facts=["coordinates equipment work"],
        forbidden_claims=[],
    )


def test_judge_payload_does_not_leak_calibration_phase_or_human_label() -> None:
    payload = judge_payload(_item())

    assert "phase" not in payload
    assert "human_label" not in payload


def test_pass_verdict_requires_perfect_scores_and_no_flags() -> None:
    with pytest.raises(ValidationError):
        JudgeVerdict(
            label="pass",
            groundedness=2,
            relevance=2,
            citation_support=1,
            completeness=2,
            error_flags=[],
            rationale="A citation only partially supports the answer.",
        )


def test_agreement_metrics_and_majority() -> None:
    human = ["pass", "fail", "pass", "fail"]
    judge = ["pass", "fail", "fail", "fail"]

    assert exact_agreement(human, judge) == 0.75
    assert cohens_kappa(human, judge) == 0.5
    assert majority_label(["fail", "pass", "fail"]) == "fail"
