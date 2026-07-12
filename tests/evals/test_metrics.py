from pathlib import Path

from scopeproof_core.demo import build_review_from_paths
from scopeproof_core.evals.metrics import EvidenceQualityMetrics
from scopeproof_core.evals.runner import run_bundled_benchmark
from scopeproof_core.schemas.models import HumanDecision, HumanResolution


def test_metrics_are_derived_from_executed_case_results() -> None:
    metrics = EvidenceQualityMetrics.from_benchmark(run_bundled_benchmark())

    assert metrics.executed_case_count == 12
    assert metrics.executed_criterion_count == 13
    assert metrics.must_have_false_ready == 0
    assert metrics.false_blocker == 0
    assert metrics.evidence_link_precision == 1.0
    assert metrics.incorrect_line_citation_rate == 0.0
    assert metrics.criterion_agreement_rate == 1.0
    assert metrics.human_override_rate is None
    assert metrics.accepted_exception_rate is None
    assert metrics.unresolved_ambiguity_rate is None


def test_metrics_derive_human_rates_from_selected_review_bundles() -> None:
    root = Path("evals")
    complete = build_review_from_paths(
        root / "fixtures/complete_implementation_pr.json",
        root / "labels/benchmark_complete_implementation.json",
    )
    analytics = build_review_from_paths(
        root / "fixtures/analytics_omitted_pr.json",
        root / "labels/benchmark_analytics_omitted.json",
    )
    analytics.resolutions.append(
        HumanResolution(
            criterion_id="AC-02",
            decision=HumanDecision.ACCEPTED_EXCEPTION,
            comment="Accepted for this release",
        )
    )
    ambiguous = build_review_from_paths(
        root / "fixtures/ambiguous_criterion_pr.json",
        root / "labels/benchmark_ambiguous_criterion.json",
    )

    metrics = EvidenceQualityMetrics.from_benchmark_and_reviews(
        run_bundled_benchmark(), [complete, analytics, ambiguous]
    )

    assert metrics.human_override_rate == 0.25
    assert metrics.accepted_exception_rate == 1 / 3
    assert metrics.unresolved_ambiguity_rate == 0.25
