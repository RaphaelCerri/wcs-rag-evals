from pathlib import Path

from wcs_rag_evals.contracts import load_golden_set, load_source_manifest
from wcs_rag_evals.fetch_corpus import _matches

ROOT = Path(__file__).resolve().parents[1]


def test_every_relevant_document_is_selected_by_the_source_manifest() -> None:
    manifest = load_source_manifest(ROOT / "corpus" / "sources.yaml")
    sources = {source.id: source for source in manifest.sources}
    cases = load_golden_set(ROOT / "evals" / "datasets" / "golden-v0.1.jsonl")

    for case in cases:
        for document_id in case.relevant_documents:
            source_id, relative_path = document_id.split("/", 1)
            source = sources[source_id]
            assert _matches(relative_path, source.include), document_id
            assert not _matches(relative_path, source.exclude), document_id


def test_manifest_does_not_select_agent_instructions_or_deployment() -> None:
    manifest = load_source_manifest(ROOT / "corpus" / "sources.yaml")
    repo = next(source for source in manifest.sources if source.id == "openwcs-repo")

    assert not _matches("CLAUDE.md", repo.include)
    assert not _matches("AgentTeamOrchestration.md", repo.include)
    assert not _matches("deploy/README.md", repo.include)
