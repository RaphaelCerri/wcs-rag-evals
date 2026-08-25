"""Tune RRF on dev only and evaluate hybrid BM25 plus dense retrieval."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from wcs_rag_evals.contracts import GoldenCase, load_golden_set
from wcs_rag_evals.evaluate_bm25 import case_metrics, sha256_file, summarize
from wcs_rag_evals.rrf import FusedDocument, reciprocal_rank_fusion

RANK_CONSTANTS = (10, 20, 40, 60)
DENSE_WEIGHTS = (0.5, 0.75, 1.0, 1.25, 1.5)


def _documents(case: dict[str, Any]) -> list[str]:
    return [item["document_id"] for item in case["retrieved_documents"]]


def _fuse_case(
    case_id: str,
    bm25_cases: dict[str, dict[str, Any]],
    dense_cases: dict[str, dict[str, Any]],
    rank_constant: int,
    dense_weight: float,
) -> list[FusedDocument]:
    return reciprocal_rank_fusion(
        {
            "bm25": _documents(bm25_cases[case_id]),
            "dense": _documents(dense_cases[case_id]),
        },
        weights={"bm25": 1.0, "dense": dense_weight},
        rank_constant=rank_constant,
        limit=10,
    )


def _evaluate_cases(
    cases: list[GoldenCase],
    bm25_cases: dict[str, dict[str, Any]],
    dense_cases: dict[str, dict[str, Any]],
    rank_constant: int,
    dense_weight: float,
) -> list[dict[str, Any]]:
    evaluated: list[dict[str, Any]] = []
    for case in cases:
        ranking = _fuse_case(
            case.id,
            bm25_cases,
            dense_cases,
            rank_constant,
            dense_weight,
        )
        retrieved = [item.document_id for item in ranking]
        evaluated.append(
            {
                "id": case.id,
                "metrics": case_metrics(retrieved, set(case.relevant_documents)),
            }
        )
    return evaluated


def select_configuration(
    dev_cases: list[GoldenCase],
    bm25_cases: dict[str, dict[str, Any]],
    dense_cases: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    trials: list[dict[str, Any]] = []
    for rank_constant in RANK_CONSTANTS:
        for dense_weight in DENSE_WEIGHTS:
            results = _evaluate_cases(
                dev_cases,
                bm25_cases,
                dense_cases,
                rank_constant,
                dense_weight,
            )
            summary = summarize(results)
            trials.append(
                {
                    "rank_constant": rank_constant,
                    "weights": {"bm25": 1.0, "dense": dense_weight},
                    "dev_metrics": summary,
                }
            )

    def selection_key(trial: dict[str, Any]) -> tuple[float, float, float, float, int]:
        metrics = trial["dev_metrics"]
        return (
            metrics["ndcg_at_10"],
            metrics["recall_at_5"],
            metrics["mrr_at_10"],
            -abs(trial["weights"]["dense"] - 1.0),
            trial["rank_constant"],
        )

    selected = max(trials, key=selection_key)
    return selected, trials


def _validate_inputs(bm25: dict[str, Any], dense: dict[str, Any]) -> None:
    if bm25["dataset"]["sha256"] != dense["dataset"]["sha256"]:
        raise ValueError("source reports use different golden sets")
    if bm25["corpus"]["manifest_sha256"] != dense["corpus"]["manifest_sha256"]:
        raise ValueError("source reports use different corpora")
    if bm25["configuration"]["chunking"] != dense["configuration"]["chunking"]:
        raise ValueError("source reports use different chunking")


def evaluate(
    bm25_path: Path,
    dense_path: Path,
    dataset_path: Path,
) -> dict[str, Any]:
    bm25 = json.loads(bm25_path.read_text(encoding="utf-8"))
    dense = json.loads(dense_path.read_text(encoding="utf-8"))
    _validate_inputs(bm25, dense)
    golden_cases = load_golden_set(dataset_path)
    bm25_cases = {case["id"]: case for case in bm25["cases"]}
    dense_cases = {case["id"]: case for case in dense["cases"]}

    dev_cases = [case for case in golden_cases if case.answerable and case.split == "dev"]
    selected, trials = select_configuration(dev_cases, bm25_cases, dense_cases)
    rank_constant = selected["rank_constant"]
    dense_weight = selected["weights"]["dense"]

    evaluated: list[dict[str, Any]] = []
    unanswerable: list[dict[str, Any]] = []
    for case in golden_cases:
        ranking = _fuse_case(
            case.id,
            bm25_cases,
            dense_cases,
            rank_constant,
            dense_weight,
        )
        retrieved = [item.document_id for item in ranking]
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
                    "score": round(item.score, 9),
                    "source_ranks": item.ranks,
                    "source_contributions": {
                        name: round(value, 9) for name, value in item.contributions.items()
                    },
                }
                for rank, item in enumerate(ranking, start=1)
            ],
        }
        if not case.answerable:
            result["evaluation"] = "excluded_from_retrieval_metrics"
            unanswerable.append(result)
            continue
        result["metrics"] = case_metrics(retrieved, set(case.relevant_documents))
        result["source_metrics"] = {
            "bm25": bm25_cases[case.id]["metrics"],
            "dense": dense_cases[case.id]["metrics"],
        }
        result["metric_deltas"] = {
            source: {
                metric: round(value - source_metrics[metric], 6)
                for metric, value in result["metrics"].items()
            }
            for source, source_metrics in result["source_metrics"].items()
        }
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
    summaries = {name: summarize(cases) for name, cases in sorted(groups.items())}

    return {
        "schema_version": "1.0",
        "baseline": "hybrid-rrf-v0.1",
        "configuration": {
            "method": "weighted_reciprocal_rank_fusion",
            "selection_split": "dev",
            "selection_objective": ["ndcg_at_10", "recall_at_5", "mrr_at_10"],
            "selected": {
                "rank_constant": rank_constant,
                "weights": selected["weights"],
            },
            "candidate_grid": {
                "rank_constants": list(RANK_CONSTANTS),
                "dense_weights": list(DENSE_WEIGHTS),
                "bm25_weight": 1.0,
            },
            "ranking_level": "document",
            "source_depth": 10,
            "k_values": [1, 3, 5, 10],
        },
        "corpus": bm25["corpus"],
        "dataset": {
            **bm25["dataset"],
            "path": dataset_path.as_posix(),
            "sha256": sha256_file(dataset_path),
        },
        "source_reports": {
            "bm25": {"path": bm25_path.as_posix(), "sha256": sha256_file(bm25_path)},
            "dense": {"path": dense_path.as_posix(), "sha256": sha256_file(dense_path)},
        },
        "tuning_trials": trials,
        "summaries": summaries,
        "source_summaries": {"bm25": bm25["summaries"], "dense": dense["summaries"]},
        "cases": evaluated + unanswerable,
    }


def render_markdown(report: dict[str, Any]) -> str:
    selected = report["configuration"]["selected"]
    lines = [
        "# Hybrid retrieval with RRF v0.1",
        "",
        "Comparação reproduzível entre BM25, dense retrieval e rank fusion.",
        "Os parâmetros foram selecionados exclusivamente nos 12 casos respondíveis de `dev`;",
        "o split `test` foi usado somente depois da seleção.",
        "",
        "## Configuração selecionada",
        "",
        "- Método: weighted Reciprocal Rank Fusion",
        f"- Constante de rank: {selected['rank_constant']}",
        f"- Peso BM25: {selected['weights']['bm25']}",
        f"- Peso dense: {selected['weights']['dense']}",
        "- Profundidade de cada fonte: top 10 documentos",
        "- Objetivo de seleção: nDCG@10, Recall@5 e MRR@10 em `dev`",
        "",
        "## Comparação",
        "",
        "| Grupo | Retriever | R@5 | R@10 | MRR@10 | nDCG@10 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for group in ("all", "dev", "test", "language:en", "language:pt-BR"):
        if group not in report["summaries"]:
            continue
        for name, summaries in (
            ("BM25", report["source_summaries"]["bm25"]),
            ("Dense", report["source_summaries"]["dense"]),
            ("Hybrid RRF", report["summaries"]),
        ):
            values = summaries[group]
            lines.append(
                f"| {group} | {name} | {values['recall_at_5']:.3f} | "
                f"{values['recall_at_10']:.3f} | {values['mrr_at_10']:.3f} | "
                f"{values['ndcg_at_10']:.3f} |"
            )
    lines.extend(
        [
            "",
            "## Resultado por caso",
            "",
            "| Caso | Split | Idioma | Primeiro relevante | R@5 | Δ BM25 | Δ Dense | Top 1 |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for case in report["cases"]:
        if not case["answerable"]:
            continue
        top_one = case["retrieved_documents"][0]["document_id"]
        rank = case["first_relevant_rank"] or "não encontrado"
        lines.append(
            f"| {case['id']} | {case['split']} | {case['language']} | {rank} | "
            f"{case['metrics']['recall_at_5']:.3f} | "
            f"{case['metric_deltas']['bm25']['recall_at_5']:+.3f} | "
            f"{case['metric_deltas']['dense']['recall_at_5']:+.3f} | `{top_one}` |"
        )
    lines.extend(
        [
            "",
            "## Reproduzir",
            "",
            "```powershell",
            "wcs-eval-hybrid",
            "```",
            "",
            "A execução usa os relatórios versionados de BM25 e dense retrieval.",
            "O JSON registra os 20 trials de `dev`, ranks e contribuição de cada fonte.",
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
    parser.add_argument("--bm25", type=Path, default=Path("evals/results/bm25-v0.1.json"))
    parser.add_argument("--dense", type=Path, default=Path("evals/results/dense-v0.1.json"))
    parser.add_argument("--dataset", type=Path, default=Path("evals/datasets/golden-v0.1.jsonl"))
    parser.add_argument("--json", type=Path, default=Path("evals/results/hybrid-v0.1.json"))
    parser.add_argument("--markdown", type=Path, default=Path("evals/results/hybrid-v0.1.md"))
    args = parser.parse_args()
    report = evaluate(args.bm25, args.dense, args.dataset)
    write_report(report, args.json, args.markdown)
    summary = report["summaries"]["all"]
    selected = report["configuration"]["selected"]
    print(
        f"Selected RRF k={selected['rank_constant']}, dense_weight="
        f"{selected['weights']['dense']}: Recall@5={summary['recall_at_5']:.3f}, "
        f"nDCG@10={summary['ndcg_at_10']:.3f}"
    )


if __name__ == "__main__":
    main()
