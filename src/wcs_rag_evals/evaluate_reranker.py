"""Rerank hybrid candidates with a pinned multilingual cross-encoder."""

from __future__ import annotations

import argparse
import json
import platform
from collections import defaultdict
from math import ceil
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

from wcs_rag_evals.contracts import load_golden_set
from wcs_rag_evals.evaluate_bm25 import case_metrics, sha256_file, summarize
from wcs_rag_evals.reranker import (
    MODEL_ID,
    MODEL_REVISION,
    MultilingualReranker,
    RerankCandidate,
    rerank,
)

DEV_NDCG_MIN_DELTA = 0.010
TEST_NDCG_MIN_DELTA = 0.0
LATENCY_P95_BUDGET_MS = 15_000.0
CANDIDATE_DEPTH = 10
BATCH_SIZE = 16


def nearest_rank_percentile(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("cannot calculate a percentile from an empty sample")
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be greater than 0 and at most 1")
    ordered = sorted(values)
    return ordered[ceil(percentile * len(ordered)) - 1]


def _documents_by_id(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["document_id"]: item for item in case["retrieved_documents"]}


def build_candidates(
    hybrid_case: dict[str, Any],
    bm25_case: dict[str, Any],
    dense_case: dict[str, Any],
    chunks: dict[str, str],
) -> list[RerankCandidate]:
    sources = (_documents_by_id(bm25_case), _documents_by_id(dense_case))
    candidates: list[RerankCandidate] = []
    for document in hybrid_case["retrieved_documents"][:CANDIDATE_DEPTH]:
        document_id = document["document_id"]
        chunk_ids: list[str] = []
        for source in sources:
            source_document = source.get(document_id)
            if source_document is None:
                continue
            chunk_id = source_document["best_chunk_id"]
            if chunk_id not in chunk_ids:
                chunk_ids.append(chunk_id)
        if not chunk_ids:
            raise ValueError(f"no source passage found for hybrid candidate {document_id}")
        missing = [chunk_id for chunk_id in chunk_ids if chunk_id not in chunks]
        if missing:
            raise ValueError(f"chunks missing from source index: {missing}")
        candidates.append(
            RerankCandidate(
                document_id=document_id,
                original_rank=document["rank"],
                passages=tuple((chunk_id, chunks[chunk_id]) for chunk_id in chunk_ids),
            )
        )
    return candidates


def _validate_inputs(
    hybrid: dict[str, Any],
    bm25: dict[str, Any],
    dense: dict[str, Any],
    index: dict[str, Any],
) -> None:
    dataset_hashes = {
        hybrid["dataset"]["sha256"],
        bm25["dataset"]["sha256"],
        dense["dataset"]["sha256"],
    }
    if len(dataset_hashes) != 1:
        raise ValueError("source reports use different golden sets")
    manifest_hashes = {
        hybrid["corpus"]["manifest_sha256"],
        bm25["corpus"]["manifest_sha256"],
        dense["corpus"]["manifest_sha256"],
        index["corpus"]["manifest_sha256"],
    }
    if len(manifest_hashes) != 1:
        raise ValueError("source reports and index use different corpora")
    if bm25["configuration"]["chunking"] != index["chunking"]:
        raise ValueError("BM25 report and source index use different chunking")


def _validate_artifact_hashes(
    hybrid: dict[str, Any],
    bm25_path: Path,
    dense_path: Path,
    dataset_path: Path,
) -> None:
    if sha256_file(dataset_path) != hybrid["dataset"]["sha256"]:
        raise ValueError("golden set content differs from the source reports")
    for name, path in (("bm25", bm25_path), ("dense", dense_path)):
        if sha256_file(path) != hybrid["source_reports"][name]["sha256"]:
            raise ValueError(f"{name} report content differs from the hybrid source artifact")


def _group_summaries(evaluated: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in evaluated:
        groups["all"].append(result)
        groups[result["split"]].append(result)
        groups[f"language:{result['language']}"].append(result)
    return {name: summarize(cases) for name, cases in sorted(groups.items())}


def evaluate(
    hybrid_path: Path,
    bm25_path: Path,
    dense_path: Path,
    index_path: Path,
    dataset_path: Path,
    model: MultilingualReranker | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    hybrid = json.loads(hybrid_path.read_text(encoding="utf-8"))
    bm25 = json.loads(bm25_path.read_text(encoding="utf-8"))
    dense = json.loads(dense_path.read_text(encoding="utf-8"))
    index = json.loads(index_path.read_text(encoding="utf-8"))
    _validate_inputs(hybrid, bm25, dense, index)
    _validate_artifact_hashes(hybrid, bm25_path, dense_path, dataset_path)

    golden_cases = load_golden_set(dataset_path)
    hybrid_cases = {case["id"]: case for case in hybrid["cases"]}
    bm25_cases = {case["id"]: case for case in bm25["cases"]}
    dense_cases = {case["id"]: case for case in dense["cases"]}
    chunks = {chunk["chunk_id"]: chunk["text"] for chunk in index["chunks"]}
    candidates = {
        case.id: build_candidates(
            hybrid_cases[case.id], bm25_cases[case.id], dense_cases[case.id], chunks
        )
        for case in golden_cases
    }

    reranker = model or MultilingualReranker(device="cpu")
    first_case = golden_cases[0]
    first_candidate = candidates[first_case.id][0]
    reranker.score([(first_case.question, first_candidate.passages[0][1])], batch_size=1)

    evaluated: list[dict[str, Any]] = []
    unanswerable: list[dict[str, Any]] = []
    latencies_ms: list[float] = []
    passage_pair_counts: list[int] = []
    for case in golden_cases:
        case_candidates = candidates[case.id]
        pair_count = sum(len(candidate.passages) for candidate in case_candidates)
        started = perf_counter()
        ranking = rerank(case.question, case_candidates, reranker, batch_size=BATCH_SIZE)
        latency_ms = (perf_counter() - started) * 1_000
        latencies_ms.append(latency_ms)
        passage_pair_counts.append(pair_count)
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
                    "score": round(item.score, 6),
                    "original_hybrid_rank": item.original_rank,
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
        result["hybrid_metrics"] = hybrid_cases[case.id]["metrics"]
        result["metric_deltas"] = {
            metric: round(value - result["hybrid_metrics"][metric], 6)
            for metric, value in result["metrics"].items()
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

    summaries = _group_summaries(evaluated)
    dev_delta = round(summaries["dev"]["ndcg_at_10"] - hybrid["summaries"]["dev"]["ndcg_at_10"], 6)
    test_delta = round(
        summaries["test"]["ndcg_at_10"] - hybrid["summaries"]["test"]["ndcg_at_10"], 6
    )
    quality_gates = {
        "dev_ndcg_at_10": {
            "minimum_delta": DEV_NDCG_MIN_DELTA,
            "observed_delta": dev_delta,
            "passed": dev_delta >= DEV_NDCG_MIN_DELTA,
        },
        "test_ndcg_at_10": {
            "minimum_delta": TEST_NDCG_MIN_DELTA,
            "observed_delta": test_delta,
            "passed": test_delta >= TEST_NDCG_MIN_DELTA,
        },
    }
    quality_passed = all(gate["passed"] for gate in quality_gates.values())

    report = {
        "schema_version": "1.0",
        "experiment": "cross-encoder-reranker-v0.1",
        "configuration": {
            "model": {"id": MODEL_ID, "revision": MODEL_REVISION},
            "device": "cpu",
            "batch_size": BATCH_SIZE,
            "candidate_source": "hybrid-rrf-v0.1",
            "candidate_depth": CANDIDATE_DEPTH,
            "passage_selection": "best BM25 and dense chunk per candidate; max cross-encoder score",
            "ranking_level": "document",
            "selection_policy": "predeclared acceptance gates; no test-set tuning",
        },
        "corpus": hybrid["corpus"],
        "dataset": {
            **hybrid["dataset"],
            "path": dataset_path.as_posix(),
            "sha256": sha256_file(dataset_path),
        },
        "source_artifacts": {
            "hybrid": {"path": hybrid_path.as_posix(), "sha256": sha256_file(hybrid_path)},
            "bm25": {"path": bm25_path.as_posix(), "sha256": sha256_file(bm25_path)},
            "dense": {"path": dense_path.as_posix(), "sha256": sha256_file(dense_path)},
            "index": {"path": index_path.as_posix(), "sha256": sha256_file(index_path)},
        },
        "quality_gates": {**quality_gates, "passed": quality_passed},
        "summaries": summaries,
        "hybrid_summaries": hybrid["summaries"],
        "cases": evaluated + unanswerable,
    }
    p95_ms = nearest_rank_percentile(latencies_ms, 0.95)
    latency_passed = p95_ms <= LATENCY_P95_BUDGET_MS
    benchmark = {
        "schema_version": "1.0",
        "experiment": "cross-encoder-reranker-benchmark-v0.1",
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION},
        "runtime": {
            "device": "cpu",
            "python": platform.python_version(),
            "platform": platform.platform(),
            "batch_size": BATCH_SIZE,
            "warmup_excluded": True,
        },
        "workload": {
            "query_count": len(golden_cases),
            "candidate_depth": CANDIDATE_DEPTH,
            "passage_pairs_total": sum(passage_pair_counts),
            "passage_pairs_per_query": passage_pair_counts,
        },
        "query_latency_ms": [round(value, 3) for value in latencies_ms],
        "summary_ms": {
            "p50": round(median(latencies_ms), 3),
            "p95_nearest_rank": round(p95_ms, 3),
            "max": round(max(latencies_ms), 3),
            "total": round(sum(latencies_ms), 3),
        },
        "latency_gate": {
            "metric": "p95_nearest_rank_ms",
            "maximum": LATENCY_P95_BUDGET_MS,
            "passed": latency_passed,
        },
        "acceptance": {
            "quality_passed": quality_passed,
            "latency_passed": latency_passed,
            "accepted": quality_passed and latency_passed,
        },
    }
    return report, benchmark


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Cross-encoder reranker v0.1",
        "",
        "Reordenação dos dez documentos do Hybrid RRF com um cross-encoder multilíngue",
        "fixado por revisão. Os critérios foram declarados antes da execução e o split `test`",
        "não foi usado para selecionar configuração.",
        "",
        "## Configuração",
        "",
        f"- Modelo: `{report['configuration']['model']['id']}`",
        f"- Revisão: `{report['configuration']['model']['revision']}`",
        "- Execução: CPU, batch 16",
        "- Candidatos: top 10 do Hybrid RRF",
        "- Passagens: melhor chunk BM25 e dense por documento; prevalece o maior score",
        "",
        "## Resultado",
        "",
        "| Grupo | Sistema | R@5 | R@10 | MRR@10 | nDCG@10 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for group in ("all", "dev", "test", "language:en", "language:pt-BR"):
        if group not in report["summaries"]:
            continue
        for name, source in (
            ("Hybrid RRF", report["hybrid_summaries"]),
            ("Reranker", report["summaries"]),
        ):
            values = source[group]
            lines.append(
                f"| {group} | {name} | {values['recall_at_5']:.3f} | "
                f"{values['recall_at_10']:.3f} | {values['mrr_at_10']:.3f} | "
                f"{values['ndcg_at_10']:.3f} |"
            )
    lines.extend(["", "## Gates de qualidade", ""])
    for name, gate in report["quality_gates"].items():
        if name == "passed":
            continue
        lines.append(
            f"- `{name}`: delta {gate['observed_delta']:+.3f}; mínimo "
            f"{gate['minimum_delta']:+.3f}; **{'passou' if gate['passed'] else 'falhou'}**"
        )
    lines.extend(
        [
            "",
            "O gate de latência e a decisão agregada ficam no benchmark separado, pois tempos",
            "de execução variam por máquina e não pertencem ao artefato determinístico.",
            "",
            "## Resultado por caso",
            "",
            "| Caso | Split | Idioma | Primeiro relevante | nDCG@10 | Delta | Top 1 |",
            "|---|---|---|---:|---:|---:|---|",
        ]
    )
    for case in report["cases"]:
        if not case["answerable"]:
            continue
        top_one = case["retrieved_documents"][0]["document_id"]
        first_rank = case["first_relevant_rank"] or "não encontrado"
        lines.append(
            f"| {case['id']} | {case['split']} | {case['language']} | {first_rank} | "
            f"{case['metrics']['ndcg_at_10']:.3f} | "
            f"{case['metric_deltas']['ndcg_at_10']:+.3f} | `{top_one}` |"
        )
    lines.extend(["", "## Reproduzir", "", "```powershell", "wcs-eval-reranker", "```", ""])
    return "\n".join(lines)


def render_benchmark_markdown(benchmark: dict[str, Any]) -> str:
    summary = benchmark["summary_ms"]
    gate = benchmark["latency_gate"]
    acceptance = benchmark["acceptance"]
    return "\n".join(
        [
            "# Reranker CPU benchmark v0.1",
            "",
            f"- Consultas: {benchmark['workload']['query_count']}",
            f"- Pares query-passage: {benchmark['workload']['passage_pairs_total']}",
            f"- p50: {summary['p50']:.3f} ms",
            f"- p95 (nearest-rank): {summary['p95_nearest_rank']:.3f} ms",
            f"- Máximo: {summary['max']:.3f} ms",
            f"- Orçamento p95: {gate['maximum']:.0f} ms",
            f"- Gate de latência: **{'passou' if gate['passed'] else 'falhou'}**",
            "- Gates de qualidade: "
            f"**{'passaram' if acceptance['quality_passed'] else 'falharam'}**",
            f"- Decisão: **{'aceito' if acceptance['accepted'] else 'não aceito'}**",
            "",
            "Warm-up excluído. Os tempos medidos variam de acordo com hardware e carga da máquina.",
            "",
        ]
    )


def write_reports(
    report: dict[str, Any],
    benchmark: dict[str, Any],
    json_path: Path,
    markdown_path: Path,
    benchmark_json_path: Path,
    benchmark_markdown_path: Path,
) -> None:
    for path in (json_path, markdown_path, benchmark_json_path, benchmark_markdown_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    benchmark_json_path.write_text(
        json.dumps(benchmark, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    benchmark_markdown_path.write_text(render_benchmark_markdown(benchmark), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hybrid", type=Path, default=Path("evals/results/hybrid-v0.1.json"))
    parser.add_argument("--bm25", type=Path, default=Path("evals/results/bm25-v0.1.json"))
    parser.add_argument("--dense", type=Path, default=Path("evals/results/dense-v0.1.json"))
    parser.add_argument("--index", type=Path, default=Path(".data/index/bm25-v0.1.json"))
    parser.add_argument("--dataset", type=Path, default=Path("evals/datasets/golden-v0.1.jsonl"))
    parser.add_argument("--json", type=Path, default=Path("evals/results/reranker-v0.1.json"))
    parser.add_argument("--markdown", type=Path, default=Path("evals/results/reranker-v0.1.md"))
    parser.add_argument(
        "--benchmark-json",
        type=Path,
        default=Path("evals/results/reranker-benchmark-v0.1.json"),
    )
    parser.add_argument(
        "--benchmark-markdown",
        type=Path,
        default=Path("evals/results/reranker-benchmark-v0.1.md"),
    )
    args = parser.parse_args()
    report, benchmark = evaluate(args.hybrid, args.bm25, args.dense, args.index, args.dataset)
    write_reports(
        report,
        benchmark,
        args.json,
        args.markdown,
        args.benchmark_json,
        args.benchmark_markdown,
    )
    summary = report["summaries"]["all"]
    print(
        f"Reranker: Recall@5={summary['recall_at_5']:.3f}, "
        f"nDCG@10={summary['ndcg_at_10']:.3f}, "
        f"p95={benchmark['summary_ms']['p95_nearest_rank']:.1f} ms, "
        f"accepted={benchmark['acceptance']['accepted']}"
    )


if __name__ == "__main__":
    main()
