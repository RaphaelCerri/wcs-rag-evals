"""Generate cited answers and compare grounded RAG with a no-retrieval control."""

from __future__ import annotations

import argparse
import json
import platform
from collections import defaultdict
from pathlib import Path
from statistics import fmean, median
from time import perf_counter
from typing import Any

from wcs_rag_evals.bm25 import tokenize
from wcs_rag_evals.contracts import GoldenCase, load_golden_set
from wcs_rag_evals.evaluate_bm25 import sha256_file
from wcs_rag_evals.evaluate_reranker import nearest_rank_percentile
from wcs_rag_evals.generation import (
    EXTRACTIVE_GENERATOR_ID,
    ExtractiveGenerator,
    GenerationContext,
    GenerationResult,
    Generator,
)

CANDIDATE_DEPTH = 3
MAX_PASSAGE_WORDS = 120
FACT_TOKEN_RECALL_THRESHOLD = 0.55
SCHEMA_VALID_RATE_MIN = 1.0
CITATION_VALIDITY_RATE_MIN = 1.0
REFUSAL_ACCURACY_MIN = 1.0
RELEVANT_CITATION_HIT_RATE_MIN = 0.80
DEV_FACT_COVERAGE_MIN_DELTA = 0.10
LATENCY_P95_BUDGET_MS = 30_000.0


def _round(value: float) -> float:
    return round(value, 6)


def _document_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["document_id"]: item for item in case["retrieved_documents"]}


def build_contexts(
    hybrid_case: dict[str, Any],
    bm25_case: dict[str, Any],
    dense_case: dict[str, Any],
    chunks: dict[str, str],
) -> list[GenerationContext]:
    source_maps = (_document_map(bm25_case), _document_map(dense_case))
    contexts: list[GenerationContext] = []
    for document in hybrid_case["retrieved_documents"][:CANDIDATE_DEPTH]:
        document_id = document["document_id"]
        chunk_ids: list[str] = []
        for source in source_maps:
            item = source.get(document_id)
            if item is not None and item["best_chunk_id"] not in chunk_ids:
                chunk_ids.append(item["best_chunk_id"])
        if not chunk_ids:
            raise ValueError(f"no source chunk found for {document_id}")
        missing = [chunk_id for chunk_id in chunk_ids if chunk_id not in chunks]
        if missing:
            raise ValueError(f"chunks missing from source index: {missing}")
        contexts.append(
            GenerationContext(
                document_id=document_id,
                passages=tuple(
                    (chunk_id, " ".join(chunks[chunk_id].split()[:MAX_PASSAGE_WORDS]))
                    for chunk_id in chunk_ids
                ),
            )
        )
    return contexts


def token_f1(candidate: str, reference: str) -> float:
    candidate_tokens = tokenize(candidate)
    reference_tokens = tokenize(reference)
    if not candidate_tokens or not reference_tokens:
        return 0.0
    candidate_counts: dict[str, int] = defaultdict(int)
    reference_counts: dict[str, int] = defaultdict(int)
    for token in candidate_tokens:
        candidate_counts[token] += 1
    for token in reference_tokens:
        reference_counts[token] += 1
    overlap = sum(
        min(count, reference_counts.get(token, 0)) for token, count in candidate_counts.items()
    )
    precision = overlap / len(candidate_tokens)
    recall = overlap / len(reference_tokens)
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def required_fact_coverage(answer: str, required_facts: list[str]) -> float | None:
    if not required_facts:
        return None
    answer_tokens = set(tokenize(answer))
    matches = 0
    for fact in required_facts:
        fact_tokens = set(tokenize(fact))
        recall = len(answer_tokens & fact_tokens) / len(fact_tokens) if fact_tokens else 0.0
        matches += recall >= FACT_TOKEN_RECALL_THRESHOLD
    return matches / len(required_facts)


def extractive_bigram_support(answer: str, evidence: str) -> float:
    answer_tokens = tokenize(answer)
    evidence_tokens = tokenize(evidence)
    answer_bigrams = set(zip(answer_tokens, answer_tokens[1:], strict=False))
    if not answer_bigrams:
        return 0.0
    evidence_bigrams = set(zip(evidence_tokens, evidence_tokens[1:], strict=False))
    return len(answer_bigrams & evidence_bigrams) / len(answer_bigrams)


def _normalized_contains(text: str, claim: str) -> bool:
    return " ".join(tokenize(claim)) in " ".join(tokenize(text))


def evaluate_answer(
    case: GoldenCase,
    result: GenerationResult,
    contexts: list[GenerationContext],
    *,
    use_retrieval: bool,
) -> dict[str, Any]:
    available = {context.document_id for context in contexts} if use_retrieval else set()
    relevant = set(case.relevant_documents)
    citations = set(result.citations)
    cited_evidence = " ".join(
        text
        for context in contexts
        if context.document_id in citations
        for _, text in context.passages
    )
    relevant_hit = bool(citations & relevant) if case.answerable and use_retrieval else None
    citation_precision = (
        len(citations & relevant) / len(citations)
        if citations and case.answerable and use_retrieval
        else None
    )
    citation_recall = (
        len(citations & relevant) / len(relevant)
        if relevant and case.answerable and use_retrieval
        else None
    )
    fact_coverage = required_fact_coverage(result.answer, case.required_facts)
    return {
        "schema_valid": result.schema_valid,
        "answerability_correct": result.answerable == case.answerable,
        "citation_valid": citations <= available,
        "relevant_citation_hit": relevant_hit,
        "gold_citation_precision": _round(citation_precision)
        if citation_precision is not None
        else None,
        "gold_citation_recall": _round(citation_recall) if citation_recall is not None else None,
        "reference_token_f1": _round(token_f1(result.answer, case.reference_answer)),
        "required_fact_coverage_proxy": _round(fact_coverage)
        if fact_coverage is not None
        else None,
        "extractive_bigram_support_proxy": _round(
            extractive_bigram_support(result.answer, cited_evidence)
        )
        if use_retrieval and citations
        else None,
        "forbidden_claim_lexical_hits": sum(
            _normalized_contains(result.answer, claim) for claim in case.forbidden_claims
        ),
        "refusal_correct": (not result.answerable) if not case.answerable else None,
    }


def _serialize_result(result: GenerationResult) -> dict[str, Any]:
    return {
        "answerable": result.answerable,
        "answer": result.answer,
        "citations": list(result.citations),
        "schema_valid": result.schema_valid,
        "raw_output": result.raw_output,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "parse_error": result.parse_error,
    }


def _deserialize_result(raw: dict[str, Any]) -> GenerationResult:
    return GenerationResult(
        answerable=raw["answerable"],
        answer=raw["answer"],
        citations=tuple(raw["citations"]),
        schema_valid=raw["schema_valid"],
        raw_output=raw["raw_output"],
        input_tokens=raw["input_tokens"],
        output_tokens=raw["output_tokens"],
        parse_error=raw.get("parse_error"),
    )


class GenerationCache:
    def __init__(self, path: Path, fingerprint: dict[str, Any]) -> None:
        self.path = path
        self.fingerprint = fingerprint
        self.records: dict[str, dict[str, Any]] = {}
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw.get("fingerprint") == fingerprint:
                self.records = raw.get("records", {})

    def get(self, key: str) -> tuple[GenerationResult, float] | None:
        record = self.records.get(key)
        if record is None:
            return None
        return _deserialize_result(record["result"]), float(record["latency_ms"])

    def put(self, key: str, result: GenerationResult, latency_ms: float) -> None:
        self.records[key] = {
            "result": _serialize_result(result),
            "latency_ms": round(latency_ms, 3),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                {"fingerprint": self.fingerprint, "records": self.records},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)


def _summarize_outputs(cases: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    outputs = [case["outputs"][mode] for case in cases]
    metric_names = list(outputs[0]["metrics"])
    summary: dict[str, Any] = {"case_count": len(outputs)}
    for name in metric_names:
        values = [output["metrics"][name] for output in outputs]
        present = [float(value) for value in values if value is not None]
        if present:
            summary[name] = _round(fmean(present))
    summary["input_tokens_total"] = sum(output["input_tokens"] for output in outputs)
    summary["output_tokens_total"] = sum(output["output_tokens"] for output in outputs)
    return summary


def _summaries(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        groups["all"].append(case)
        groups[case["split"]].append(case)
        groups[f"language:{case['language']}"].append(case)
    return {
        group: {
            mode: _summarize_outputs(group_cases, mode) for mode in ("grounded", "no_retrieval")
        }
        for group, group_cases in sorted(groups.items())
    }


def _run_generation(
    generator: Generator | None,
    cache: GenerationCache,
    key: str,
    question: str,
    contexts: list[GenerationContext],
    use_retrieval: bool,
) -> tuple[GenerationResult, float]:
    cached = cache.get(key)
    if cached is not None:
        return cached
    if generator is None:
        raise RuntimeError("generation provider was not initialized for a cache miss")
    started = perf_counter()
    result = generator.generate(question, contexts, use_retrieval=use_retrieval)
    latency_ms = (perf_counter() - started) * 1_000
    cache.put(key, result, latency_ms)
    print(f"Generated {key} in {latency_ms:.1f} ms")
    return result, latency_ms


def evaluate(
    hybrid_path: Path,
    bm25_path: Path,
    dense_path: Path,
    index_path: Path,
    dataset_path: Path,
    cache_path: Path,
    generator: Generator | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    hybrid = json.loads(hybrid_path.read_text(encoding="utf-8"))
    bm25 = json.loads(bm25_path.read_text(encoding="utf-8"))
    dense = json.loads(dense_path.read_text(encoding="utf-8"))
    index = json.loads(index_path.read_text(encoding="utf-8"))
    dataset_hash = sha256_file(dataset_path)
    if dataset_hash != hybrid["dataset"]["sha256"]:
        raise ValueError("golden set content differs from the hybrid report")
    if sha256_file(bm25_path) != hybrid["source_reports"]["bm25"]["sha256"]:
        raise ValueError("BM25 report content differs from the hybrid source artifact")
    if sha256_file(dense_path) != hybrid["source_reports"]["dense"]["sha256"]:
        raise ValueError("dense report content differs from the hybrid source artifact")
    if index["corpus"]["manifest_sha256"] != hybrid["corpus"]["manifest_sha256"]:
        raise ValueError("source index and hybrid report use different corpora")

    golden_cases = load_golden_set(dataset_path)
    hybrid_cases = {case["id"]: case for case in hybrid["cases"]}
    bm25_cases = {case["id"]: case for case in bm25["cases"]}
    dense_cases = {case["id"]: case for case in dense["cases"]}
    chunks = {chunk["chunk_id"]: chunk["text"] for chunk in index["chunks"]}
    contexts_by_case = {
        case.id: build_contexts(
            hybrid_cases[case.id], bm25_cases[case.id], dense_cases[case.id], chunks
        )
        for case in golden_cases
    }
    fingerprint = {
        "generator": EXTRACTIVE_GENERATOR_ID,
        "dataset_sha256": dataset_hash,
        "hybrid_sha256": sha256_file(hybrid_path),
        "index_sha256": sha256_file(index_path),
        "candidate_depth": CANDIDATE_DEPTH,
        "max_passage_words": MAX_PASSAGE_WORDS,
    }
    cache = GenerationCache(cache_path, fingerprint)
    expected_keys = {
        f"{case.id}:{mode}" for case in golden_cases for mode in ("grounded", "no_retrieval")
    }
    cache_complete = expected_keys <= set(cache.records)
    provider = generator or (None if cache_complete else ExtractiveGenerator())

    cases: list[dict[str, Any]] = []
    latencies: dict[str, list[float]] = {"grounded": [], "no_retrieval": []}
    for case in golden_cases:
        contexts = contexts_by_case[case.id]
        outputs: dict[str, Any] = {}
        for mode, use_retrieval in (("grounded", True), ("no_retrieval", False)):
            result, latency_ms = _run_generation(
                provider,
                cache,
                f"{case.id}:{mode}",
                case.question,
                contexts,
                use_retrieval,
            )
            latencies[mode].append(latency_ms)
            serialized = _serialize_result(result)
            serialized.pop("raw_output")
            serialized["metrics"] = evaluate_answer(
                case, result, contexts, use_retrieval=use_retrieval
            )
            outputs[mode] = serialized
        cases.append(
            {
                "id": case.id,
                "question": case.question,
                "split": case.split,
                "language": case.language,
                "category": case.category,
                "answerable": case.answerable,
                "relevant_documents": case.relevant_documents,
                "retrieved_documents": [context.document_id for context in contexts],
                "outputs": outputs,
            }
        )

    summaries = _summaries(cases)
    grounded_all = summaries["all"]["grounded"]
    grounded_dev = summaries["dev"]["grounded"]
    control_dev = summaries["dev"]["no_retrieval"]
    dev_delta = _round(
        grounded_dev["required_fact_coverage_proxy"] - control_dev["required_fact_coverage_proxy"]
    )
    unanswerable_grounded = [
        case["outputs"]["grounded"]["metrics"]["refusal_correct"]
        for case in cases
        if not case["answerable"]
    ]
    refusal_accuracy = fmean(float(value) for value in unanswerable_grounded)
    quality_gates = {
        "schema_valid_rate": {
            "minimum": SCHEMA_VALID_RATE_MIN,
            "observed": grounded_all["schema_valid"],
            "passed": grounded_all["schema_valid"] >= SCHEMA_VALID_RATE_MIN,
        },
        "citation_validity_rate": {
            "minimum": CITATION_VALIDITY_RATE_MIN,
            "observed": grounded_all["citation_valid"],
            "passed": grounded_all["citation_valid"] >= CITATION_VALIDITY_RATE_MIN,
        },
        "refusal_accuracy": {
            "minimum": REFUSAL_ACCURACY_MIN,
            "observed": _round(refusal_accuracy),
            "passed": refusal_accuracy >= REFUSAL_ACCURACY_MIN,
        },
        "relevant_citation_hit_rate": {
            "minimum": RELEVANT_CITATION_HIT_RATE_MIN,
            "observed": grounded_all["relevant_citation_hit"],
            "passed": grounded_all["relevant_citation_hit"] >= RELEVANT_CITATION_HIT_RATE_MIN,
        },
        "dev_fact_coverage_delta": {
            "minimum": DEV_FACT_COVERAGE_MIN_DELTA,
            "observed": dev_delta,
            "passed": dev_delta >= DEV_FACT_COVERAGE_MIN_DELTA,
        },
    }
    quality_passed = all(gate["passed"] for gate in quality_gates.values())
    report = {
        "schema_version": "1.0",
        "experiment": "extractive-grounded-baseline-v0.1",
        "configuration": {
            "provider": "deterministic_local",
            "generator": EXTRACTIVE_GENERATOR_ID,
            "selection": "best query-overlap sentence from each retrieved document",
            "retrieval": "hybrid-rrf-v0.1",
            "candidate_depth": CANDIDATE_DEPTH,
            "max_passage_words": MAX_PASSAGE_WORDS,
            "passages_per_document": "best BM25 and dense chunk, deduplicated",
            "control": "deterministic refusal without retrieved sources",
            "estimated_api_cost_usd": 0.0,
        },
        "metric_scope": {
            "deterministic": [
                "schema validity",
                "answerability classification",
                "citation ID validity",
                "gold-document citation precision and recall",
                "reference token F1",
                "required-fact lexical coverage proxy",
                "extractive bigram support proxy",
                "exact forbidden-claim lexical hits",
            ],
            "not_claimed_until_calibrated_judge": [
                "semantic faithfulness",
                "semantic answer relevance",
                "claim-level citation entailment",
            ],
        },
        "corpus": hybrid["corpus"],
        "dataset": {**hybrid["dataset"], "path": dataset_path.as_posix()},
        "source_artifacts": {
            "hybrid": {"path": hybrid_path.as_posix(), "sha256": sha256_file(hybrid_path)},
            "bm25": {"path": bm25_path.as_posix(), "sha256": sha256_file(bm25_path)},
            "dense": {"path": dense_path.as_posix(), "sha256": sha256_file(dense_path)},
            "index": {"path": index_path.as_posix(), "sha256": sha256_file(index_path)},
        },
        "quality_gates": {**quality_gates, "passed": quality_passed},
        "summaries": summaries,
        "cases": cases,
    }

    latency_summaries = {
        mode: {
            "p50": round(median(values), 3),
            "p95_nearest_rank": round(nearest_rank_percentile(values, 0.95), 3),
            "max": round(max(values), 3),
            "total": round(sum(values), 3),
        }
        for mode, values in latencies.items()
    }
    grounded_p95 = latency_summaries["grounded"]["p95_nearest_rank"]
    latency_passed = grounded_p95 <= LATENCY_P95_BUDGET_MS
    benchmark = {
        "schema_version": "1.0",
        "experiment": "extractive-generation-benchmark-v0.1",
        "generator": EXTRACTIVE_GENERATOR_ID,
        "runtime": {
            "device": "cpu",
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cache_path": cache_path.as_posix(),
        },
        "workload": {
            "case_count": len(cases),
            "generation_count": len(cases) * 2,
            "modes": ["grounded", "no_retrieval"],
        },
        "latency_ms": {
            mode: [round(value, 3) for value in values] for mode, values in latencies.items()
        },
        "summary_ms": latency_summaries,
        "tokens": {
            mode: {
                "input_total": summaries["all"][mode]["input_tokens_total"],
                "output_total": summaries["all"][mode]["output_tokens_total"],
            }
            for mode in ("grounded", "no_retrieval")
        },
        "cost": {"provider_api_cost_usd": 0.0, "local_compute_not_monetized": True},
        "latency_gate": {
            "metric": "grounded_p95_nearest_rank_ms",
            "maximum": LATENCY_P95_BUDGET_MS,
            "observed": grounded_p95,
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
        "# Extractive grounded baseline v0.1",
        "",
        "Baseline local que extrai evidências com citações e recusa quando não há retrieval.",
        "Os gates foram definidos antes da geração. Métricas semânticas dependentes de judge",
        "ficam explicitamente fora desta fase.",
        "",
        "## Comparação",
        "",
        "| Grupo | Modo | Schema | Answerability | Citation hit | Fact coverage | Token F1 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for group in ("all", "dev", "test", "language:en", "language:pt-BR"):
        if group not in report["summaries"]:
            continue
        for mode, name in (("grounded", "RAG"), ("no_retrieval", "Sem retrieval")):
            values = report["summaries"][group][mode]
            citation_hit = values.get("relevant_citation_hit", 0.0)
            lines.append(
                f"| {group} | {name} | {values['schema_valid']:.3f} | "
                f"{values['answerability_correct']:.3f} | {citation_hit:.3f} | "
                f"{values['required_fact_coverage_proxy']:.3f} | "
                f"{values['reference_token_f1']:.3f} |"
            )
    lines.extend(["", "## Gates", ""])
    for name, gate in report["quality_gates"].items():
        if name == "passed":
            continue
        lines.append(
            f"- `{name}`: observado {gate['observed']:.3f}; mínimo {gate['minimum']:.3f}; "
            f"**{'passou' if gate['passed'] else 'falhou'}**"
        )
    lines.extend(
        [
            "",
            "## Limite de interpretação",
            "",
            "Citation hit mede sobreposição com documentos rotulados, não entailment por claim.",
            "Fact coverage e suporte extrativo são proxies lexicais. Faithfulness semântica e",
            "citation correctness por claim exigem o judge calibrado da próxima fase.",
            "",
            "## Respostas",
            "",
        ]
    )
    for case in report["cases"]:
        output = case["outputs"]["grounded"]
        lines.extend(
            [
                f"### {case['id']}",
                "",
                output["answer"],
                "",
                "Citações: "
                + (", ".join(f"`{item}`" for item in output["citations"]) or "nenhuma"),
                "",
            ]
        )
    return "\n".join(lines)


def render_benchmark_markdown(benchmark: dict[str, Any]) -> str:
    grounded = benchmark["summary_ms"]["grounded"]
    control = benchmark["summary_ms"]["no_retrieval"]
    acceptance = benchmark["acceptance"]
    return "\n".join(
        [
            "# Grounded generation CPU benchmark v0.1",
            "",
            f"- Gerações: {benchmark['workload']['generation_count']}",
            f"- RAG p50: {grounded['p50']:.3f} ms",
            f"- RAG p95: {grounded['p95_nearest_rank']:.3f} ms",
            f"- Controle p50: {control['p50']:.3f} ms",
            f"- Controle p95: {control['p95_nearest_rank']:.3f} ms",
            f"- API cost: US$ {benchmark['cost']['provider_api_cost_usd']:.2f}",
            f"- Gate de latência: **{'passou' if acceptance['latency_passed'] else 'falhou'}**",
            "- Gates de qualidade: "
            f"**{'passaram' if acceptance['quality_passed'] else 'falharam'}**",
            f"- Decisão como baseline: **{'aceito' if acceptance['accepted'] else 'não aceito'}**",
            "",
            "Tempos medidos em CPU variam conforme hardware, carga e estado do cache do sistema.",
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
    parser.add_argument("--cache", type=Path, default=Path(".data/generation/extractive-v0.1.json"))
    parser.add_argument("--json", type=Path, default=Path("evals/results/generation-v0.1.json"))
    parser.add_argument("--markdown", type=Path, default=Path("evals/results/generation-v0.1.md"))
    parser.add_argument(
        "--benchmark-json",
        type=Path,
        default=Path("evals/results/generation-benchmark-v0.1.json"),
    )
    parser.add_argument(
        "--benchmark-markdown",
        type=Path,
        default=Path("evals/results/generation-benchmark-v0.1.md"),
    )
    args = parser.parse_args()
    report, benchmark = evaluate(
        args.hybrid,
        args.bm25,
        args.dense,
        args.index,
        args.dataset,
        args.cache,
    )
    write_reports(
        report,
        benchmark,
        args.json,
        args.markdown,
        args.benchmark_json,
        args.benchmark_markdown,
    )
    grounded = report["summaries"]["all"]["grounded"]
    print(
        f"Generation: fact_coverage={grounded['required_fact_coverage_proxy']:.3f}, "
        f"citation_hit={grounded['relevant_citation_hit']:.3f}, "
        f"p95={benchmark['summary_ms']['grounded']['p95_nearest_rank']:.1f} ms, "
        f"accepted={benchmark['acceptance']['accepted']}"
    )


if __name__ == "__main__":
    main()
