"""Calibrate and validate an LLM judge against explicitly sourced reference labels."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Literal

from wcs_rag_evals.evaluate_bm25 import sha256_file
from wcs_rag_evals.judge import (
    EVIDENCE_ORDER_POLICIES,
    INPUT_USD_PER_MILLION,
    JUDGE_MODEL,
    JUDGE_PROMPT_VERSION,
    OUTPUT_USD_PER_MILLION,
    OpenAIJudge,
    cohens_kappa,
    exact_agreement,
    judge_configuration_sha256,
    majority_label,
)
from wcs_rag_evals.judge_contracts import AnnotationItem, ReferenceAnnotation

Phase = Literal["calibration", "validation"]
VALIDATION_EXACT_AGREEMENT_MIN = 0.80
VALIDATION_KAPPA_MIN = 0.60
POSITION_STABILITY_MIN = 0.90
SAFETY_REFUSAL_CASE_ID = "wcs-test-004"


def _read_jsonl(path: Path, model: type[Any]) -> list[Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [model.model_validate_json(line) for line in lines if line]


def _unique_by_case_id(records: list[Any], source: str) -> dict[str, Any]:
    ids = [record.case_id for record in records]
    duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate case IDs in {source}: {', '.join(duplicates)}")
    return {record.case_id: record for record in records}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


class JudgeCache:
    def __init__(self, path: Path, packet_sha256: str, configuration_sha256: str) -> None:
        self.path = path
        self.packet_sha256 = packet_sha256
        self.configuration_sha256 = configuration_sha256
        self.records: dict[str, dict[str, Any]] = {}
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if (
                raw.get("packet_sha256") == packet_sha256
                and raw.get("configuration_sha256") == configuration_sha256
            ):
                self.records = raw.get("records", {})

    def save(self) -> None:
        _write_json(
            self.path,
            {
                "configuration_sha256": self.configuration_sha256,
                "packet_sha256": self.packet_sha256,
                "records": self.records,
            },
        )


def _agreement(cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not cases:
        return {"case_count": 0, "exact_agreement": None, "cohens_kappa": None}
    reference = [case["reference_label"] for case in cases]
    judge = [case["judge_label"] for case in cases]
    return {
        "case_count": len(cases),
        "exact_agreement": round(exact_agreement(reference, judge), 6),
        "cohens_kappa": round(cohens_kappa(reference, judge), 6),
        "confusion": {
            f"reference_{left}__judge_{right}": sum(
                expected == left and observed == right
                for expected, observed in zip(reference, judge, strict=True)
            )
            for left in ("pass", "fail")
            for right in ("pass", "fail")
        },
    }


def _validate_seal(
    root: Path,
    configuration_sha256: str,
    calibration_labels_sha256: str,
    validation_labels_sha256: str,
) -> dict[str, Any]:
    seal_path = root / "evals/judges/judge-calibration-seal-v0.1.json"
    if not seal_path.exists():
        raise ValueError(
            "validation is sealed until calibration creates judge-calibration-seal-v0.1.json"
        )
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    if seal["configuration_sha256"] != configuration_sha256:
        raise ValueError("judge configuration changed after calibration seal")
    if seal["calibration_labels_sha256"] != calibration_labels_sha256:
        raise ValueError("calibration labels changed after calibration seal")
    if seal["validation_labels_sha256"] != validation_labels_sha256:
        raise ValueError("validation labels changed after calibration seal")
    calibration_path = root / seal["calibration_report_path"]
    if sha256_file(calibration_path) != seal["calibration_report_sha256"]:
        raise ValueError("calibration report changed after seal")
    return seal


def _write_calibration_seal(
    root: Path,
    report_path: Path,
    configuration_sha256: str,
    calibration_labels_sha256: str,
    validation_labels_sha256: str,
) -> None:
    _write_json(
        root / "evals/judges/judge-calibration-seal-v0.1.json",
        {
            "schema_version": "1.0",
            "configuration_sha256": configuration_sha256,
            "calibration_labels_sha256": calibration_labels_sha256,
            "validation_labels_sha256": validation_labels_sha256,
            "calibration_report_path": report_path.relative_to(root).as_posix(),
            "calibration_report_sha256": sha256_file(report_path),
            "validation_gates": {
                "exact_agreement_min": VALIDATION_EXACT_AGREEMENT_MIN,
                "cohens_kappa_min": VALIDATION_KAPPA_MIN,
                "position_stability_min": POSITION_STABILITY_MIN,
                "safety_refusal_case_must_match": SAFETY_REFUSAL_CASE_ID,
            },
        },
    )


def run(
    root: Path,
    phase: Phase,
    repeats: int = 3,
    provider: OpenAIJudge | None = None,
) -> dict[str, Any]:
    if repeats < 3 or repeats % 2 == 0:
        raise ValueError("repeats must be an odd number of at least 3")
    packet_path = root / "reports/judge/calibration-packet-v0.1.jsonl"
    calibration_labels_path = root / "evals/judges/agent-proxy-calibration-labels-v0.1.jsonl"
    validation_labels_path = root / "evals/judges/agent-proxy-validation-labels-v0.1.jsonl"
    labels_path = calibration_labels_path if phase == "calibration" else validation_labels_path
    all_items = _read_jsonl(packet_path, AnnotationItem)
    items = [item for item in all_items if item.phase == phase]
    labels = _read_jsonl(labels_path, ReferenceAnnotation)
    item_map = _unique_by_case_id(items, f"{phase} packet")
    label_map = _unique_by_case_id(labels, f"{phase} reference labels")
    extra = sorted(set(label_map) - set(item_map))
    missing = sorted(set(item_map) - set(label_map))
    if extra or missing:
        raise ValueError(f"reference label coverage mismatch; extra={extra}, missing={missing}")
    unsure = [item.case_id for item in items if label_map[item.case_id].label == "unsure"]

    packet_sha256 = sha256_file(packet_path)
    labels_sha256 = sha256_file(labels_path)
    calibration_labels_sha256 = sha256_file(calibration_labels_path)
    validation_labels_sha256 = sha256_file(validation_labels_path)
    configuration_sha256 = judge_configuration_sha256()
    seal = None
    if phase == "validation":
        seal = _validate_seal(
            root,
            configuration_sha256,
            calibration_labels_sha256,
            validation_labels_sha256,
        )

    cache = JudgeCache(root / "reports/judge-cache-v0.1.json", packet_sha256, configuration_sha256)
    judge = provider or OpenAIJudge()
    results: list[dict[str, Any]] = []
    for item in items:
        calls: list[dict[str, Any]] = []
        for repetition in range(1, repeats + 1):
            evidence_order = EVIDENCE_ORDER_POLICIES[
                (repetition - 1) % len(EVIDENCE_ORDER_POLICIES)
            ]
            key = f"{phase}:{item.case_id}:{repetition}:{evidence_order}"
            if key not in cache.records:
                call = judge.evaluate(item, evidence_order)
                cache.records[key] = {
                    "evidence_order": evidence_order,
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
                "reference_label": label_map[item.case_id].label,
                "judge_label": judge_label,
                "position_stable": len({call["verdict"]["label"] for call in calls}) == 1,
                "calls": calls,
            }
        )

    comparable = [case for case in results if case["case_id"] not in unsure]
    agreement = _agreement(comparable)
    stability = round(sum(case["position_stable"] for case in results) / len(results), 6)
    promotion_gate = None
    if phase == "validation":
        safety_case = next(case for case in comparable if case["case_id"] == SAFETY_REFUSAL_CASE_ID)
        promotion_gate = {
            "exact_agreement": agreement["exact_agreement"] >= VALIDATION_EXACT_AGREEMENT_MIN,
            "cohens_kappa": agreement["cohens_kappa"] >= VALIDATION_KAPPA_MIN,
            "position_stability": stability >= POSITION_STABILITY_MIN,
            "safety_refusal_case": safety_case["judge_label"] == safety_case["reference_label"],
        }
        promotion_gate["passed"] = all(promotion_gate.values())

    report = {
        "schema_version": "1.0",
        "experiment": "agent-proxy-llm-judge-v0.1",
        "phase": phase,
        "reference_type": "model_assisted_adjudication",
        "human_calibration_claimed": False,
        "model": JUDGE_MODEL,
        "prompt_version": JUDGE_PROMPT_VERSION,
        "configuration_sha256": configuration_sha256,
        "packet_sha256": packet_sha256,
        "reference_labels_sha256": labels_sha256,
        "repeats": repeats,
        "evidence_order_policies": list(EVIDENCE_ORDER_POLICIES),
        "pricing_usd_per_million_tokens": {
            "input": INPUT_USD_PER_MILLION,
            "output": OUTPUT_USD_PER_MILLION,
        },
        "excluded_unsure_cases": unsure,
        "agreement": agreement,
        "position_stability_rate": stability,
        "estimated_cost_usd": round(
            sum(call["estimated_cost_usd"] for case in results for call in case["calls"]), 6
        ),
        "validation_seal": seal,
        "promotion_gate": promotion_gate,
        "cases": results,
    }
    report_path = root / f"evals/results/judge-{phase}-v0.1.json"
    _write_json(report_path, report)
    if phase == "calibration":
        _write_calibration_seal(
            root,
            report_path,
            configuration_sha256,
            calibration_labels_sha256,
            validation_labels_sha256,
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--phase", choices=("calibration", "validation"), required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is not configured")
    report = run(args.root.resolve(), args.phase, args.repeats)
    print(json.dumps(report["agreement"], indent=2))


if __name__ == "__main__":
    main()
