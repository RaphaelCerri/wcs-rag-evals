"""Fail CI when versioned evaluation artifacts cross preregistered quality floors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from wcs_rag_evals.evaluate_bm25 import sha256_file


def _value_at(document: dict[str, Any], dotted_path: str) -> Any:
    value: Any = document
    for segment in dotted_path.split("."):
        if not isinstance(value, dict) or segment not in value:
            raise ValueError(f"missing metric path: {dotted_path}")
        value = value[segment]
    return value


def _passes(operator: str, observed: float, threshold: float) -> bool:
    if operator == "gte":
        return observed >= threshold
    if operator == "lte":
        return observed <= threshold
    raise ValueError(f"unsupported regression operator: {operator}")


def evaluate_policy(policy: dict[str, Any], artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for check in policy["checks"]:
        observed = _value_at(artifacts[check["artifact"]], check["path"])
        if isinstance(observed, bool) or not isinstance(observed, (int, float)):
            raise ValueError(f"metric is not numeric: {check['id']}")
        passed = _passes(check["operator"], float(observed), float(check["threshold"]))
        results.append({**check, "observed": observed, "passed": passed})
    return {
        "policy_id": policy["policy_id"],
        "baseline_commit": policy["baseline_commit"],
        "passed": all(result["passed"] for result in results),
        "checks": results,
        "known_gaps": policy.get("known_gaps", []),
    }


def _validate_provenance(root: Path, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    tracked: list[tuple[str, dict[str, Any]]] = []
    hybrid = artifacts["hybrid"]
    generation = artifacts["generation"]
    tracked.extend(
        (f"hybrid_source_{name}", value) for name, value in hybrid["source_reports"].items()
    )
    tracked.append(("hybrid_dataset", hybrid["dataset"]))
    tracked.extend(
        (f"generation_source_{name}", value)
        for name, value in generation["source_artifacts"].items()
        if not value["path"].startswith(".data/")
    )
    tracked.append(("generation_dataset", generation["dataset"]))
    results = []
    for name, artifact in tracked:
        path = root / artifact["path"]
        observed = sha256_file(path)
        expected = artifact["sha256"]
        results.append(
            {
                "id": name,
                "path": artifact["path"],
                "expected_sha256": expected,
                "observed_sha256": observed,
                "passed": observed == expected,
            }
        )
    return results


def check(root: Path) -> dict[str, Any]:
    policy_path = root / "evals/regression-policy-v0.1.yaml"
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    artifacts = {
        name: json.loads((root / path).read_text(encoding="utf-8"))
        for name, path in policy["artifacts"].items()
    }
    report = evaluate_policy(policy, artifacts)
    provenance = _validate_provenance(root, artifacts)
    report["provenance"] = provenance
    report["passed"] = report["passed"] and all(item["passed"] for item in provenance)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = check(args.root.resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
