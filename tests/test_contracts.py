from pathlib import Path

import pytest
from pydantic import ValidationError

from wcs_rag_evals.contracts import GoldenCase, load_golden_set, load_source_manifest

ROOT = Path(__file__).resolve().parents[1]


def test_source_manifest_is_revision_pinned_and_unique() -> None:
    manifest = load_source_manifest(ROOT / "corpus" / "sources.yaml")

    assert {source.id for source in manifest.sources} == {"openwcs-repo", "openwcs-wiki"}
    assert all(len(source.revision) == 40 for source in manifest.sources)
    assert all(source.license == "AGPL-3.0-only" for source in manifest.sources)


def test_golden_set_has_both_splits_and_an_unanswerable_case() -> None:
    cases = load_golden_set(ROOT / "evals" / "datasets" / "golden-v0.1.jsonl")

    assert len(cases) == 18
    assert {case.split for case in cases} == {"dev", "test"}
    assert sum(case.split == "dev" for case in cases) == 12
    assert sum(case.split == "test" for case in cases) == 6
    assert any(not case.answerable for case in cases)
    assert any(case.language == "pt-BR" for case in cases)


def test_every_labeled_document_uses_a_known_source_prefix() -> None:
    cases = load_golden_set(ROOT / "evals" / "datasets" / "golden-v0.1.jsonl")

    for case in cases:
        assert all(
            document.startswith(("openwcs-repo/", "openwcs-wiki/"))
            for document in case.relevant_documents
        )


def test_answerable_case_cannot_omit_evidence() -> None:
    with pytest.raises(ValidationError, match="require at least one relevant document"):
        GoldenCase.model_validate(
            {
                "id": "wcs-dev-999",
                "split": "dev",
                "category": "architecture",
                "difficulty": "basic",
                "language": "en",
                "answerable": True,
                "question": "Which component owns this example responsibility?",
                "relevant_documents": [],
                "reference_answer": "A deliberately invalid example answer.",
                "required_facts": ["one fact"],
                "forbidden_claims": [],
            }
        )


def test_unanswerable_case_cannot_label_relevant_evidence() -> None:
    with pytest.raises(ValidationError, match="cannot label a relevant document"):
        GoldenCase.model_validate(
            {
                "id": "wcs-test-999",
                "split": "test",
                "category": "unanswerable",
                "difficulty": "adversarial",
                "language": "en",
                "answerable": False,
                "question": "What secret value is not present in this public corpus?",
                "relevant_documents": ["openwcs-repo/README.md"],
                "reference_answer": "The corpus cannot answer this question.",
                "required_facts": [],
                "forbidden_claims": ["invent a secret"],
            }
        )
