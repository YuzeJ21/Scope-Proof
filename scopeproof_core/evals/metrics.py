"""Truthful evidence-quality metrics derived from executed benchmark output."""

from __future__ import annotations

from pydantic import BaseModel, Field

from scopeproof_core.evals.runner import BenchmarkResult
from scopeproof_core.schemas.models import FindingStatus, HumanDecision, ReviewBundle

_OVERRIDE_DECISIONS = {
    HumanDecision.ACCEPTED_EXCEPTION,
    HumanDecision.CHANGE_REQUIRED,
    HumanDecision.MANUALLY_VERIFIED,
    HumanDecision.NOT_IN_SCOPE,
    HumanDecision.REJECTED_FINDING,
}


class EvidenceQualityMetrics(BaseModel):
    """Metrics that describe executed fixture labels, not product correctness."""

    executed_case_count: int = Field(ge=0)
    executed_criterion_count: int = Field(ge=0)
    evidence_link_precision: float = Field(ge=0, le=1)
    incorrect_line_citation_rate: float = Field(ge=0, le=1)
    criterion_agreement_rate: float = Field(ge=0, le=1)
    must_have_false_ready: int = Field(ge=0)
    false_blocker: int = Field(ge=0)
    human_override_rate: float | None = None
    accepted_exception_rate: float | None = None
    unresolved_ambiguity_rate: float | None = None

    @classmethod
    def from_benchmark(cls, benchmark: BenchmarkResult) -> EvidenceQualityMetrics:
        """Calculate only measurements supported by actual benchmark executions."""

        checked_links = sum(case.evidence_link_count for case in benchmark.case_results)
        invalid_links = sum(len(case.evidence_link_errors) for case in benchmark.case_results)
        expected_statuses = sum(case.expected_status_count for case in benchmark.case_results)
        status_mismatches = sum(case.status_mismatch_count for case in benchmark.case_results)
        evidence_link_precision = (
            1.0 if not checked_links else (checked_links - invalid_links) / checked_links
        )
        criterion_agreement_rate = (
            1.0
            if not expected_statuses
            else (expected_statuses - status_mismatches) / expected_statuses
        )
        return cls(
            executed_case_count=benchmark.executed_case_count,
            executed_criterion_count=benchmark.executed_criterion_count,
            evidence_link_precision=evidence_link_precision,
            incorrect_line_citation_rate=1 - evidence_link_precision,
            criterion_agreement_rate=criterion_agreement_rate,
            must_have_false_ready=benchmark.must_have_false_ready,
            false_blocker=benchmark.false_blocker,
        )

    @classmethod
    def from_benchmark_and_reviews(
        cls, benchmark: BenchmarkResult, reviews: list[ReviewBundle]
    ) -> EvidenceQualityMetrics:
        """Add human rates from selected persisted-review-shaped bundles only."""

        metrics = cls.from_benchmark(benchmark)
        criteria_count = sum(len(bundle.criteria) for bundle in reviews)
        resolutions = [resolution for bundle in reviews for resolution in bundle.resolutions]
        unresolved = sum(
            len(bundle.criteria)
            if not bundle.review.criteria_confirmed
            else sum(
                finding.status is FindingStatus.NEEDS_REVIEW for finding in bundle.findings
            )
            for bundle in reviews
        )
        overrides = sum(resolution.decision in _OVERRIDE_DECISIONS for resolution in resolutions)
        exceptions = sum(
            resolution.decision is HumanDecision.ACCEPTED_EXCEPTION for resolution in resolutions
        )
        if not criteria_count:
            return metrics
        return metrics.model_copy(
            update={
                "human_override_rate": overrides / criteria_count,
                "accepted_exception_rate": (exceptions / len(resolutions)) if resolutions else 0.0,
                "unresolved_ambiguity_rate": unresolved / criteria_count,
            }
        )
