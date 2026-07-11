"""Truthful evidence-quality metrics derived from executed benchmark output."""

from __future__ import annotations

from pydantic import BaseModel, Field

from scopeproof_core.evals.runner import BenchmarkResult


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
