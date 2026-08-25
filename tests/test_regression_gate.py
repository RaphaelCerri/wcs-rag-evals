from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from wcs_rag_evals.regression_gate import check, evaluate_policy

ROOT = Path(__file__).resolve().parents[1]


def test_versioned_artifacts_pass_regression_policy() -> None:
    report = check(ROOT)

    assert report["passed"] is True
    assert all(item["passed"] for item in report["checks"])
    assert all(item["passed"] for item in report["provenance"])


def test_deliberate_quality_regression_fails_gate() -> None:
    policy = yaml.safe_load(
        (ROOT / "evals/regression-policy-v0.1.yaml").read_text(encoding="utf-8")
    )
    artifacts = {
        name: json.loads((ROOT / path).read_text(encoding="utf-8"))
        for name, path in policy["artifacts"].items()
    }
    regressed = copy.deepcopy(artifacts)
    regressed["hybrid"]["summaries"]["test"]["recall_at_5"] = 0.0

    report = evaluate_policy(policy, regressed)

    failed = {item["id"] for item in report["checks"] if not item["passed"]}
    assert report["passed"] is False
    assert failed == {"hybrid_test_recall_at_5"}
