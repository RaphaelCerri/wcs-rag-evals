"""Run a repeated LLM judge and measure agreement against untouched human labels."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from wcs_rag_evals.evaluate_bm25 import sha256_file
from wcs_rag_evals.judge import (
    INPUT_USD_PER_MILLION,
    JUDGE_MODEL,
    JUDGE_PROMPT_VERSION,
    OUTPUT_USD_PER_MILLION,
    OpenAIJudge,
    cohens_kappa,
    exact_agreement,
    majority_label,
)
from wcs_rag_evals.judge_contracts import AnnotationItem, HumanAnnotation


def _read_jsonl(path: Path, model: type[Any]) -> list[Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [model.model_validate_json(line) for line in lines if line]


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


class JudgeCache:
    def __init__(self, path: Path, packet_sha256: str) -> None:
        self.path = path
        self.packet_sha256 = packet_sha256
        self.records: dict[str, dict[str, Any]] = {}
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            same_model = raw.get("model") == JUDGE_MODEL
            same_prompt = raw.get("prompt_version") == JUDGE_PROMPT_VERSION
            same_packet = raw.get("packet_sha256") == packet_sha256
            if same_model and same_prompt and same_packet:
                self.records = raw.get("records", {})

    def save(self) -> None:
        _write_json(
            self.path,
            {
                "model": JUDGE_MODEL,
                "prompt_version": JUDGE_PROMPT_VERSION,
                "packet_sha256": self.packet_sha256,
                "records": self.records,
            },
        )


def _agreement(cases: list[dict[str, Any]]) -> dict[str, Any]:
    human = [case["human_label"] for case in cases]
    judge = [case["judge_label"] for case in cases]
    return {
        "case_count": len(cases),
        "exact_agreement": round(exact_agreement(human, judge), 6),
        "cohens_kappa": round(cohens_kappa(human, judge), 6),
        "confusion": {
            f"human_{left}__judge_{right}": sum(
                h == left and j == right for h, j in zip(human, judge, strict=True)
            )
            for left in ("pass", "fail")
            for right in ("pass", "fail")
        },
    }


def run(root: Path, repeats: int = 3) -> dict[str, Any]:
    if repeats < 3 or repeats % 2 == 0:
        raise ValueError("repeats must be an odd number of at least 3")
    packet_path = root / "reports/judge/calibration-packet-v0.1.jsonl"
    labels_path = root / "evals/judges/human-labels-v0.1.jsonl"
    items = _read_jsonl(packet_path, AnnotationItem)
    labels = {label.case_id: label for label in _read_jsonl(labels_path, HumanAnnotation)}
    missing = [
        item.case_id
        for item in items
        if item.case_id not in labels or labels[item.case_id].label is None
    ]
    if missing:
        raise ValueError("human labels are incomplete: " + ", ".join(missing))
    unsure = [item.case_id for item in items if labels[item.case_id].label == "unsure"]

    packet_sha256 = sha256_file(packet_path)
    labels_sha256 = sha256_file(labels_path)
    cache = JudgeCache(root / "reports/judge-cache-v0.1.json", packet_sha256)
    provider = OpenAIJudge()
    results: list[dict[str, Any]] = []
    for item in items:
        calls: list[dict[str, Any]] = []
        for repetition in range(1, repeats + 1):
            key = f"{item.case_id}:{repetition}"
            if key not in cache.records:
                call = provider.evaluate(item)
                cache.records[key] = {
                    "verdict": call.verdict.model_dump(mode="json"),
                    "input_tokens": call.input_tokens,
                    "output_tokens": call.output_tokens,
                    "latency_ms": call.latency_ms,
                    "response_id": call.response_id,
                    "estimated_cost_usd": round(call.estimated_cost_usd, 8),
                }
                cache.save()
            calls.append(cache.records[key])
        judge_label = majority_label([call["verdict"]["label"] for call in calls])
        results.append(
            {
                "case_id": item.case_id,
                "phase": item.phase,
                "human_label": labels[item.case_id].label,
                "judge_label": judge_label,
                "stable": len({call["verdict"]["label"] for call in calls}) == 1,
                "calls": calls,
            }
        )

    comparable = [case for case in results if case["case_id"] not in unsure]
    report = {
        "schema_version": "1.0",
        "experiment": "calibrated-llm-judge-v0.1",
        "model": JUDGE_MODEL,
        "prompt_version": JUDGE_PROMPT_VERSION,
        "packet_sha256": packet_sha256,
        "human_labels_sha256": labels_sha256,
        "repeats": repeats,
        "pricing_usd_per_million_tokens": {
            "input": INPUT_USD_PER_MILLION,
            "output": OUTPUT_USD_PER_MILLION,
        },
        "excluded_unsure_cases": unsure,
        "agreement": {
            phase: _agreement([case for case in comparable if case["phase"] == phase])
            for phase in ("calibration", "validation")
        },
        "judge_stability_rate": round(sum(case["stable"] for case in results) / len(results), 6),
        "estimated_cost_usd": round(
            sum(call["estimated_cost_usd"] for case in results for call in case["calls"]), 6
        ),
        "cases": results,
    }
    _write_json(root / "evals/results/judge-v0.1.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is not configured")
    report = run(args.root.resolve(), args.repeats)
    print(json.dumps(report["agreement"], indent=2))


if __name__ == "__main__":
    main()
