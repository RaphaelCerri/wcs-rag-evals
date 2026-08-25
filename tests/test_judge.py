from __future__ import annotations

import pytest
from pydantic import ValidationError

from wcs_rag_evals.evaluate_judge import _unique_by_case_id, run
from wcs_rag_evals.judge import (
    JudgeCall,
    cohens_kappa,
    exact_agreement,
    judge_configuration_sha256,
    judge_payload,
    majority_label,
)
from wcs_rag_evals.judge_contracts import (
    AnnotationItem,
    EvidencePassage,
    HumanAnnotation,
    JudgeVerdict,
    ReferenceAnnotation,
)


class FakeJudge:
    def __init__(self) -> None:
        self.orders: list[str] = []

    def evaluate(self, item: AnnotationItem, evidence_order: str) -> JudgeCall:
        self.orders.append(evidence_order)
        return JudgeCall(
            verdict=JudgeVerdict(
                label="pass",
                groundedness=2,
                relevance=2,
                citation_support=2,
                completeness=2,
                error_flags=[],
                rationale="The answer satisfies the supplied reference.",
            ),
            input_tokens=100,
            output_tokens=20,
            latency_ms=1.0,
            response_id=f"fake-{item.case_id}-{evidence_order}",
        )


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
            ),
            EvidencePassage(
                document_id="inventory.md",
                chunk_id="inventory.md::1",
                text="Inventory remains upstream of equipment execution.",
                cited=False,
            ),
        ],
        reference_answer="It coordinates equipment work.",
        required_facts=["coordinates equipment work"],
        forbidden_claims=[],
    )


def test_judge_payload_does_not_leak_calibration_phase_or_human_label() -> None:
    payload = judge_payload(_item())

    assert "phase" not in payload
    assert "human_label" not in payload


def test_evidence_order_probes_are_deterministic() -> None:
    normal = judge_payload(_item(), "retrieval")["retrieved_evidence"]
    reverse = judge_payload(_item(), "reverse")["retrieved_evidence"]
    rotate = judge_payload(_item(), "rotate")["retrieved_evidence"]

    assert reverse == list(reversed(normal))
    assert rotate == normal[1:] + normal[:1]
    assert len(judge_configuration_sha256()) == 64


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


def test_completed_human_label_requires_qualification() -> None:
    with pytest.raises(ValidationError):
        HumanAnnotation(case_id="wcs-dev-001", reviewer="Reviewer", label="pass")


def test_agent_reference_requires_two_blind_unanimous_votes() -> None:
    with pytest.raises(ValidationError):
        ReferenceAnnotation(
            case_id="wcs-dev-001",
            reference_type="model_assisted_adjudication",
            label="fail",
            error_flags=["material_omission"],
            rationale="A required fact is missing.",
            votes=[
                {
                    "role": "CEA",
                    "label": "fail",
                    "blinded_to_persisted_labels": False,
                },
                {
                    "role": "CSA",
                    "label": "pass",
                    "blinded_to_persisted_labels": True,
                },
            ],
        )


def test_duplicate_reference_ids_are_rejected() -> None:
    records = [HumanAnnotation(case_id="same"), HumanAnnotation(case_id="same")]

    with pytest.raises(ValueError, match="duplicate"):
        _unique_by_case_id(records, "test")


def test_validation_requires_calibration_seal_and_uses_separate_calls(tmp_path) -> None:
    calibration = _item()
    validation = _item().model_copy(
        update={"case_id": "wcs-test-004", "phase": "validation", "split": "test"}
    )
    packet_dir = tmp_path / "reports/judge"
    labels_dir = tmp_path / "evals/judges"
    packet_dir.mkdir(parents=True)
    labels_dir.mkdir(parents=True)
    packet = packet_dir / "calibration-packet-v0.1.jsonl"
    packet.write_text(
        calibration.model_dump_json() + "\n" + validation.model_dump_json() + "\n",
        encoding="utf-8",
    )
    votes = [
        {
            "role": "CSA",
            "label": "pass",
            "blinded_to_persisted_labels": True,
        },
        {
            "role": "CFA-reviewer",
            "label": "pass",
            "blinded_to_persisted_labels": True,
        },
    ]
    for phase, item in (("calibration", calibration), ("validation", validation)):
        reference = ReferenceAnnotation(
            case_id=item.case_id,
            reference_type="model_assisted_adjudication",
            label="pass",
            rationale="Independent reviewers accepted the answer.",
            votes=votes,
        )
        (labels_dir / f"agent-proxy-{phase}-labels-v0.1.jsonl").write_text(
            reference.model_dump_json() + "\n",
            encoding="utf-8",
        )

    with pytest.raises(ValueError, match="sealed"):
        run(tmp_path, "validation", provider=FakeJudge())

    calibration_provider = FakeJudge()
    run(tmp_path, "calibration", provider=calibration_provider)
    validation_provider = FakeJudge()
    report = run(tmp_path, "validation", provider=validation_provider)

    assert calibration_provider.orders == ["retrieval", "reverse", "rotate"]
    assert validation_provider.orders == ["retrieval", "reverse", "rotate"]
    assert report["promotion_gate"]["passed"] is True
