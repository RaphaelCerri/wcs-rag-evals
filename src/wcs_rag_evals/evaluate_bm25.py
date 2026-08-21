"""Evaluate the BM25 document ranking against the versioned golden set."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any

from wcs_rag_evals.bm25 import BM25Index
from wcs_rag_evals.chunking import Chunk
from wcs_rag_evals.contracts import load_golden_set
from wcs_rag_evals.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank

DEFAULT_K_VALUES = (1, 3, 5, 10)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _round(value: float) -> float:
    return round(value, 6)


def case_metrics(retrieved: list[str], relevant: set[str]) -> dict[str, float]:
    values: dict[str, float] = {}
    for k in DEFAULT_K_VALUES:
        values[f"recall_at_{k}"] = _round(recall_at_k(retrieved, relevant, k))
        values[f"precision_at_{k}"] = _round(precision_at_k(retrieved, relevant, k))
        values[f"ndcg_at_{k}"] = _round(ndcg_at_k(retrieved, relevant, k))
    values["mrr_at_10"] = _round(reciprocal_rank(retrieved[:10], relevant))
    return values


def summarize(cases: list[dict[str, Any]]) -> dict[str, float | int]:
    if not cases:
        return {"case_count": 0}
    metric_names = list(cases[0]["metrics"])
    summary: dict[str, float | int] = {"case_count": len(cases)}
    for name in metric_names:
        summary[name] = _round(fmean(case["metrics"][name] for case in cases))
    return summary


def evaluate(index_path: Path, dataset_path: Path) -> dict[str, Any]:
    raw_index = json.loads(index_path.read_text(encoding="utf-8"))
    chunks = [Chunk(**raw) for raw in raw_index["chunks"]]
    retriever = raw_index["retriever"]
    index = BM25Index(chunks, k1=retriever["k1"], b=retriever["b"])
    golden_cases = load_golden_set(dataset_path)

    evaluated: list[dict[str, Any]] = []
    unanswerable: list[dict[str, Any]] = []
    for case in golden_cases:
        ranking = index.search_documents(case.question, limit=10)
        retrieved = [result.document_id for result in ranking]
        result: dict[str, Any] = {
            "id": case.id,
            "question": case.question,
            "split": case.split,
            "language": case.language,
            "category": case.category,
            "answerable": case.answerable,
            "relevant_documents": case.relevant_documents,
            "retrieved_documents": [
                {
                    "rank": rank,
                    "document_id": item.document_id,
                    "score": _round(item.score),
                    "best_chunk_id": item.best_chunk_id,
                }
                for rank, item in enumerate(ranking, start=1)
            ],
        }
        if not case.answerable:
            result["evaluation"] = "excluded_from_retrieval_metrics"
            unanswerable.append(result)
            continue
        result["metrics"] = case_metrics(retrieved, set(case.relevant_documents))
        result["first_relevant_rank"] = next(
            (
                rank
                for rank, document_id in enumerate(retrieved, start=1)
                if document_id in case.relevant_documents
            ),
            None,
        )
        evaluated.append(result)

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in evaluated:
        groups["all"].append(result)
        groups[result["split"]].append(result)
        groups[f"language:{result['language']}"].append(result)

    return {
        "schema_version": "1.0",
        "baseline": raw_index["index_id"],
        "configuration": {
            "retriever": raw_index["retriever"],
            "chunking": raw_index["chunking"],
            "ranking_level": "document",
            "document_aggregation": "maximum_chunk_score",
            "k_values": list(DEFAULT_K_VALUES),
        },
        "corpus": {
            **raw_index["corpus"],
            "chunk_count": raw_index["chunk_count"],
        },
        "dataset": {
            "path": dataset_path.as_posix(),
            "sha256": sha256_file(dataset_path),
            "case_count": len(golden_cases),
            "answerable_case_count": len(evaluated),
            "unanswerable_case_count": len(unanswerable),
        },
        "summaries": {name: summarize(cases) for name, cases in sorted(groups.items())},
        "cases": evaluated + unanswerable,
    }


def render_markdown(report: dict[str, Any]) -> str:
    config = report["configuration"]
    corpus = report["corpus"]
    dataset = report["dataset"]
    lines = [
        "# BM25 baseline v0.1",
        "",
        "Resultado reproduzível do primeiro baseline lexical do projeto.",
        "Casos não respondíveis são preservados no relatório JSON, mas não entram nas métricas",
        "de retrieval porque não possuem documentos relevantes.",
        "",
        "## Configuração",
        "",
        f"- Corpus: {corpus['document_count']} documentos e {corpus['chunk_count']} chunks",
        f"- Golden set: {dataset['answerable_case_count']} casos respondíveis e "
        f"{dataset['unanswerable_case_count']} não respondível",
        f"- Chunking: {config['chunking']['max_words']} palavras, "
        f"overlap de {config['chunking']['overlap_words']}",
        f"- BM25: k1={config['retriever']['k1']}, b={config['retriever']['b']}",
        "- Ranking: documento, usando o maior score entre seus chunks",
        "",
        "## Métricas agregadas",
        "",
        "| Grupo | Casos | R@1 | R@5 | R@10 | P@5 | P@10 | MRR@10 | nDCG@10 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for group in ("all", "dev", "test", "language:en", "language:pt-BR"):
        if group not in report["summaries"]:
            continue
        values = report["summaries"][group]
        lines.append(
            f"| {group} | {values['case_count']} | {values['recall_at_1']:.3f} | "
            f"{values['recall_at_5']:.3f} | {values['recall_at_10']:.3f} | "
            f"{values['precision_at_5']:.3f} | {values['precision_at_10']:.3f} | "
            f"{values['mrr_at_10']:.3f} | {values['ndcg_at_10']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Resultado por caso",
            "",
            "| Caso | Split | Idioma | Primeiro relevante | Recall@5 | Top 1 |",
            "|---|---|---|---:|---:|---|",
        ]
    )
    for case in report["cases"]:
        if not case["answerable"]:
            continue
        top_one = (
            case["retrieved_documents"][0]["document_id"]
            if case["retrieved_documents"]
            else "nenhum"
        )
        rank = case["first_relevant_rank"] or "não encontrado"
        lines.append(
            f"| {case['id']} | {case['split']} | {case['language']} | {rank} | "
            f"{case['metrics']['recall_at_5']:.3f} | `{top_one}` |"
        )
    lines.extend(
        [
            "",
            "## Reproduzir",
            "",
            "```powershell",
            "wcs-fetch-corpus",
            "wcs-build-index",
            "wcs-eval-bm25",
            "```",
            "",
            "O JSON ao lado contém ranking, score, melhor chunk e métricas de cada caso.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=Path(".data/index/bm25-v0.1.json"))
    parser.add_argument("--dataset", type=Path, default=Path("evals/datasets/golden-v0.1.jsonl"))
    parser.add_argument("--json", type=Path, default=Path("evals/results/bm25-v0.1.json"))
    parser.add_argument("--markdown", type=Path, default=Path("evals/results/bm25-v0.1.md"))
    args = parser.parse_args()
    report = evaluate(args.index, args.dataset)
    write_report(report, args.json, args.markdown)
    summary = report["summaries"]["all"]
    print(
        f"Evaluated {summary['case_count']} answerable cases: "
        f"Recall@5={summary['recall_at_5']:.3f}, MRR@10={summary['mrr_at_10']:.3f}"
    )


if __name__ == "__main__":
    main()
