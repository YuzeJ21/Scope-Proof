from scopeproof_core.evals.metrics import EvidenceQualityMetrics
from scopeproof_core.evals.runner import run_bundled_benchmark


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
