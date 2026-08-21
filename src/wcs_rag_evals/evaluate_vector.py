"""Evaluate multilingual E5 retrieval from pgvector against the BM25 baseline."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from wcs_rag_evals.build_vector_index import INDEX_ID
from wcs_rag_evals.contracts import load_golden_set
from wcs_rag_evals.embeddings import (
    EMBEDDING_DIMENSIONS,
    MODEL_ID,
    MODEL_REVISION,
    E5Embedder,
)
from wcs_rag_evals.evaluate_bm25 import case_metrics, sha256_file, summarize
from wcs_rag_evals.vector_store import aggregate_documents, connect, search_chunks

CANDIDATE_CHUNKS = 100


def require_database_url() -> str:
    database_url = os.environ.get("WCS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("WCS_DATABASE_URL is required; copy the value from .env.example")
    return database_url


def evaluate(
    database_url: str,
    source_index_path: Path,
    dataset_path: Path,
    baseline_path: Path,
) -> dict[str, Any]:
    source_index = json.loads(source_index_path.read_text(encoding="utf-8"))
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_cases = {case["id"]: case for case in baseline["cases"]}
    golden_cases = load_golden_set(dataset_path)
    embedder = E5Embedder()
    query_embeddings = embedder.encode_queries([case.question for case in golden_cases])
    evaluated: list[dict[str, Any]] = []
    unanswerable: list[dict[str, Any]] = []

    with connect(database_url) as connection:
        for case, query_embedding in zip(golden_cases, query_embeddings, strict=True):
            chunk_results = search_chunks(
                connection,
                INDEX_ID,
                query_embedding,
                limit=CANDIDATE_CHUNKS,
            )
            ranking = aggregate_documents(chunk_results, limit=10)
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
                        "score": round(item.score, 6),
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
            bm25_metrics = baseline_cases[case.id]["metrics"]
            result["comparison"] = {
                "bm25_metrics": bm25_metrics,
                "metric_deltas": {
                    metric: round(value - bm25_metrics[metric], 6)
                    for metric, value in result["metrics"].items()
                },
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
    baseline_summaries = baseline["summaries"]
    deltas = {
        group: {
            metric: round(float(value) - float(baseline_summaries[group][metric]), 6)
            for metric, value in summary.items()
            if metric != "case_count"
        }
        for group, summary in summaries.items()
        if group in baseline_summaries
    }
    return {
        "schema_version": "1.0",
        "baseline": INDEX_ID,
        "configuration": {
            "retriever": {
                "name": "dense",
                "model_id": MODEL_ID,
                "model_revision": MODEL_REVISION,
                "dimensions": EMBEDDING_DIMENSIONS,
                "distance": "cosine",
                "normalized_embeddings": True,
                "query_prefix": "query: ",
                "document_prefix": "passage: ",
            },
            "vector_database": {
                "engine": "PostgreSQL 17",
                "extension": "pgvector 0.8.6",
                "search_mode": "exact",
                "ann_index_available": "HNSW",
                "m": 16,
                "ef_construction": 64,
            },
            "chunking": source_index["chunking"],
            "ranking_level": "document",
            "document_aggregation": "maximum_chunk_score",
            "candidate_chunks": CANDIDATE_CHUNKS,
            "k_values": [1, 3, 5, 10],
        },
        "corpus": {
            **source_index["corpus"],
            "chunk_count": source_index["chunk_count"],
        },
        "dataset": {
            "path": dataset_path.as_posix(),
            "sha256": sha256_file(dataset_path),
            "case_count": len(golden_cases),
            "answerable_case_count": len(evaluated),
            "unanswerable_case_count": len(unanswerable),
        },
        "comparison": {
            "baseline": baseline["baseline"],
            "baseline_report_sha256": sha256_file(baseline_path),
            "metric_deltas": deltas,
        },
        "summaries": summaries,
        "cases": evaluated + unanswerable,
    }


def render_markdown(report: dict[str, Any]) -> str:
    config = report["configuration"]
    corpus = report["corpus"]
    dataset = report["dataset"]
    comparison = report["comparison"]
    lines = [
        "# Dense retrieval baseline v0.1",
        "",
        "Resultado do retrieval vetorial multilíngue persistido em PostgreSQL com pgvector.",
        "As métricas usam o mesmo corpus, chunks, golden set e ranking por documento do BM25.",
        "",
        "## Configuração",
        "",
        f"- Corpus: {corpus['document_count']} documentos e {corpus['chunk_count']} chunks",
        f"- Golden set: {dataset['answerable_case_count']} casos respondíveis e "
        f"{dataset['unanswerable_case_count']} não respondível",
        f"- Modelo: `{config['retriever']['model_id']}` em revisão fixa",
        f"- Embeddings: {config['retriever']['dimensions']} dimensões, normalizados",
        "- Banco: PostgreSQL 17 e pgvector 0.8.6, com cosine distance",
        "- Execução medida: busca exata; HNSW disponível no schema para volumes maiores",
        f"- Candidatos: {config['candidate_chunks']} chunks, agregados pelo maior score",
        "",
        "## Comparação com BM25",
        "",
        "| Grupo | Casos | R@5 | Δ R@5 | R@10 | Δ R@10 | MRR@10 | Δ MRR | nDCG@10 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for group in ("all", "dev", "test", "language:en", "language:pt-BR"):
        if group not in report["summaries"]:
            continue
        values = report["summaries"][group]
        delta = comparison["metric_deltas"][group]
        lines.append(
            f"| {group} | {values['case_count']} | {values['recall_at_5']:.3f} | "
            f"{delta['recall_at_5']:+.3f} | {values['recall_at_10']:.3f} | "
            f"{delta['recall_at_10']:+.3f} | {values['mrr_at_10']:.3f} | "
            f"{delta['mrr_at_10']:+.3f} | {values['ndcg_at_10']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Resultado por caso",
            "",
            "| Caso | Split | Idioma | Primeiro relevante | Recall@5 | Δ BM25 | Top 1 |",
            "|---|---|---|---:|---:|---:|---|",
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
            f"{case['metrics']['recall_at_5']:.3f} | "
            f"{case['comparison']['metric_deltas']['recall_at_5']:+.3f} | `{top_one}` |"
        )
    lines.extend(
        [
            "",
            "## Reproduzir",
            "",
            "```powershell",
            "docker compose up -d --wait",
            '$env:WCS_DATABASE_URL = "postgresql://wcs:wcs_local_only@localhost:55432/wcs_rag"',
            "wcs-build-index",
            "wcs-build-vector-index",
            "wcs-eval-vector",
            "```",
            "",
            "O JSON ao lado preserva configuração, hashes, rankings, scores e deltas completos.",
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
    parser.add_argument("--bm25", type=Path, default=Path("evals/results/bm25-v0.1.json"))
    parser.add_argument("--json", type=Path, default=Path("evals/results/dense-v0.1.json"))
    parser.add_argument("--markdown", type=Path, default=Path("evals/results/dense-v0.1.md"))
    args = parser.parse_args()
    report = evaluate(require_database_url(), args.index, args.dataset, args.bm25)
    write_report(report, args.json, args.markdown)
    summary = report["summaries"]["all"]
    delta = report["comparison"]["metric_deltas"]["all"]
    print(
        f"Evaluated {summary['case_count']} answerable cases: "
        f"Recall@5={summary['recall_at_5']:.3f} ({delta['recall_at_5']:+.3f} vs BM25), "
        f"MRR@10={summary['mrr_at_10']:.3f} ({delta['mrr_at_10']:+.3f})"
    )


if __name__ == "__main__":
    main()
