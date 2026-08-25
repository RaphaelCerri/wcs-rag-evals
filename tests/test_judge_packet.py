from __future__ import annotations

from wcs_rag_evals.build_judge_packet import (
    CALIBRATION_IDS,
    VALIDATION_IDS,
    write_label_template,
)
from wcs_rag_evals.judge_contracts import AnnotationItem


def test_packet_has_disjoint_calibration_and_validation_sets() -> None:
    assert len(CALIBRATION_IDS) == 8
    assert len(VALIDATION_IDS) == 5
    assert set(CALIBRATION_IDS).isdisjoint(VALIDATION_IDS)


def test_packet_builder_preserves_existing_human_labels(tmp_path) -> None:
    labels = tmp_path / "human-labels-v0.1.jsonl"
    labels.write_text("sentinel\n", encoding="utf-8")

    created = write_label_template(labels, [])

    assert created is False
    assert labels.read_text(encoding="utf-8") == "sentinel\n"


def test_packet_builder_creates_label_for_each_item(tmp_path) -> None:
    labels = tmp_path / "human-labels-v0.1.jsonl"
    item = AnnotationItem(
        case_id="wcs-dev-001",
        phase="calibration",
        split="dev",
        language="en",
        category="architecture",
        difficulty="basic",
        question="Where does the system sit in the architecture?",
        answerable=True,
        answer="It coordinates equipment.",
        citations=[],
        evidence=[],
        reference_answer="It coordinates equipment.",
        required_facts=["coordinates equipment"],
        forbidden_claims=[],
    )

    assert write_label_template(labels, [item]) is True
    assert '"label": null' in labels.read_text(encoding="utf-8")
