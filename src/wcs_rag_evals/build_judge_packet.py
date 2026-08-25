"""Build a versioned, reviewable packet for human and LLM judge calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from wcs_rag_evals.contracts import load_golden_set
from wcs_rag_evals.evaluate_bm25 import sha256_file
from wcs_rag_evals.evaluate_generation import build_contexts
from wcs_rag_evals.judge_contracts import AnnotationItem, EvidencePassage, HumanAnnotation

CALIBRATION_IDS = (
    "wcs-dev-001",
    "wcs-dev-003",
    "wcs-dev-004",
    "wcs-dev-005",
    "wcs-dev-008",
    "wcs-dev-009",
    "wcs-dev-011",
    "wcs-dev-012",
)
VALIDATION_IDS = (
    "wcs-dev-002",
    "wcs-dev-010",
    "wcs-test-003",
    "wcs-test-004",
    "wcs-test-006",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_items(root: Path) -> list[AnnotationItem]:
    report = _load_json(root / "evals/results/generation-v0.1.json")
    dataset = report["dataset"]
    artifacts = [dataset, *report["source_artifacts"].values()]
    for artifact in artifacts:
        artifact_path = root / artifact["path"]
        observed = sha256_file(artifact_path)
        if observed != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {artifact['path']}")
    bm25 = _load_json(root / "evals/results/bm25-v0.1.json")
    dense = _load_json(root / "evals/results/dense-v0.1.json")
    hybrid = _load_json(root / "evals/results/hybrid-v0.1.json")
    index = _load_json(root / ".data/index/bm25-v0.1.json")

    golden = {case.id: case for case in load_golden_set(root / "evals/datasets/golden-v0.1.jsonl")}
    generated = {case["id"]: case for case in report["cases"]}
    bm25_cases = {case["id"]: case for case in bm25["cases"]}
    dense_cases = {case["id"]: case for case in dense["cases"]}
    hybrid_cases = {case["id"]: case for case in hybrid["cases"]}
    chunks = {chunk["chunk_id"]: chunk["text"] for chunk in index["chunks"]}

    selected = [(case_id, "calibration") for case_id in CALIBRATION_IDS]
    selected += [(case_id, "validation") for case_id in VALIDATION_IDS]
    items: list[AnnotationItem] = []
    for case_id, phase in selected:
        case = golden[case_id]
        output = generated[case_id]["outputs"]["grounded"]
        contexts = build_contexts(
            hybrid_cases[case_id], bm25_cases[case_id], dense_cases[case_id], chunks
        )
        citations = set(output["citations"])
        evidence = [
            EvidencePassage(
                document_id=context.document_id,
                chunk_id=chunk_id,
                text=text,
                cited=context.document_id in citations,
            )
            for context in contexts
            for chunk_id, text in context.passages
        ]
        items.append(
            AnnotationItem(
                case_id=case.id,
                phase=phase,
                split=case.split,
                language=case.language,
                category=case.category,
                difficulty=case.difficulty,
                question=case.question,
                answerable=case.answerable,
                answer=output["answer"],
                citations=output["citations"],
                evidence=evidence,
                reference_answer=case.reference_answer,
                required_facts=case.required_facts,
                forbidden_claims=case.forbidden_claims,
            )
        )
    return items


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def _packet_markdown(items: list[AnnotationItem]) -> str:
    lines = [
        "# Pacote de calibração humana v0.1",
        "",
        "Use `RUBRIC.md` antes de rotular. O conjunto de validação fica separado para evitar",
        "ajustar o prompt aos mesmos exemplos usados na medição final.",
        "",
    ]
    for item in items:
        cited = ", ".join(item.citations) or "nenhuma"
        lines.extend(
            [
                f"## {item.case_id} | {item.phase}",
                "",
                f"**Pergunta:** {item.question}",
                "",
                f"**Resposta avaliada:** {item.answer}",
                "",
                f"**Citações declaradas:** {cited}",
                "",
                f"**Resposta de referência:** {item.reference_answer}",
                "",
                "**Evidências recuperadas:**",
                "",
            ]
        )
        for passage in item.evidence:
            marker = "CITADA" if passage.cited else "NÃO CITADA"
            lines.extend(
                [
                    f"### {marker} | `{passage.chunk_id}`",
                    "",
                    passage.text,
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_label_template(path: Path, items: list[AnnotationItem]) -> bool:
    """Create an empty human-label file once, never overwrite reviewer work."""
    if path.exists():
        return False
    _write_jsonl(
        path,
        [HumanAnnotation(case_id=item.case_id).model_dump(mode="json") for item in items],
    )
    return True


def write_packet(root: Path) -> tuple[Path, Path, Path]:
    items = build_items(root)
    report_dir = root / "reports/judge"
    labels_dir = root / "evals/judges"
    report_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    packet_jsonl = report_dir / "calibration-packet-v0.1.jsonl"
    packet_md = report_dir / "calibration-packet-v0.1.md"
    labels_path = labels_dir / "human-labels-v0.1.jsonl"
    _write_jsonl(packet_jsonl, [item.model_dump(mode="json") for item in items])
    packet_md.write_text(_packet_markdown(items), encoding="utf-8")
    write_label_template(labels_path, items)
    return packet_jsonl, packet_md, labels_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    paths = write_packet(args.root.resolve())
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
