from pathlib import Path

from wcs_rag_evals.evaluate_hybrid import evaluate


def test_hybrid_configuration_is_selected_only_from_dev() -> None:
    report = evaluate(
        Path("evals/results/bm25-v0.1.json"),
        Path("evals/results/dense-v0.1.json"),
        Path("evals/datasets/golden-v0.1.jsonl"),
    )

    assert report["configuration"]["selection_split"] == "dev"
    assert report["configuration"]["selected"] == {
        "rank_constant": 60,
        "weights": {"bm25": 1.0, "dense": 1.0},
    }
    assert len(report["tuning_trials"]) == 20
    assert all(trial["dev_metrics"]["case_count"] == 12 for trial in report["tuning_trials"])


def test_hybrid_report_preserves_source_contributions() -> None:
    report = evaluate(
        Path("evals/results/bm25-v0.1.json"),
        Path("evals/results/dense-v0.1.json"),
        Path("evals/datasets/golden-v0.1.jsonl"),
    )
    first = report["cases"][0]["retrieved_documents"][0]

    assert set(first["source_ranks"]).issubset({"bm25", "dense"})
    assert set(first["source_contributions"]) == set(first["source_ranks"])
