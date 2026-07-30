"""Unchanged-path and fixed-metric tests for the R-002 runner."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scopeproof_core.evals import r002_runner
from scopeproof_core.evals.r002_diff import parse_case_diffs
from scopeproof_core.evals.r002_models import (
    R002Metric,
    R002MetricState,
    R002VerifiedCaseLines,
    SWEbenchVerifiedRow,
)
from scopeproof_core.evals.r002_runner import (
    R002RunError,
    _build_missing_explanations,
    _decoded_json_list,
    _hard_gate_codes,
    _prepare_run_cases,
    audit_r002_redaction,
    build_r002_review,
    calculate_metrics,
    evaluate_r002_case,
    metric,
    run_r002,
)
from scopeproof_core.schemas.models import (
    CheckState,
    CIReasonCode,
    EvidenceLevel,
    FindingStatus,
    GateVerdict,
)
from tests.evals.test_r002_annotation import (
    _labels_for_universe,
    _prepared_annotation_inputs,
)


def _first_case_inputs(
    tmp_path: Path,
    payload: dict[str, object],
):
    manifest, criteria, cache = _prepared_annotation_inputs(tmp_path, payload)
    universe = __import__(
        "scopeproof_core.evals.r002_runner",
        fromlist=["build_annotation_universe"],
    ).build_annotation_universe(
        manifest=manifest,
        criteria=criteria,
        cache=cache,
    )
    labels = _labels_for_universe(criteria, universe, confirmed=True)
    case = manifest.cases[0]
    criterion_case = criteria.cases[0]
    cached_case = cache.load_index().cases[0]
    row = cache.read_model(f"rows/{case.row_sha256}", SWEbenchVerifiedRow)
    parsed = parse_case_diffs(
        case_id=case.case_id,
        patch=row.patch,
        test_patch=row.test_patch,
    )
    verified = R002VerifiedCaseLines(
        case_id=case.case_id,
        head_sha=case.verified_pr_head_sha,
        lines=cached_case.verified_lines,
    )
    return (
        manifest,
        criteria,
        cache,
        universe,
        labels,
        case,
        criterion_case,
        row,
        parsed,
        verified,
    )


def test_r002_review_preserves_static_research_boundary(
    tmp_path: Path,
    r002_manifest_payload: dict[str, object],
) -> None:
    (
        _manifest,
        _criteria,
        _cache,
        _universe,
        _labels,
        case,
        criterion_case,
        row,
        parsed,
        _verified,
    ) = _first_case_inputs(tmp_path, r002_manifest_payload)
    bundle = build_r002_review(
        case=case,
        row=row,
        criterion_case=criterion_case,
        parsed=parsed,
    )

    assert bundle.research_context is not None
    assert bundle.research_context.classification == "public_engineering_research"
    assert bundle.research_context.stage1_credit is False
    assert bundle.review.check_state is CheckState.UNAVAILABLE
    assert bundle.review.ci_observation.reason_code is CIReasonCode.NO_OBSERVATIONS
    assert bundle.review.ci_observation.collection_complete is True
    assert bundle.review.ci_observation.total_check_runs == 0
    assert bundle.runtime_evidence == []
    assert bundle.resolutions == []
    assert bundle.review.final_acceptance is False
    assert all(
        item.evidence_level in {EvidenceLevel.E1, EvidenceLevel.E2} for item in bundle.evidence
    )
    assert bundle.gate.verdict in {
        GateVerdict.BLOCKED,
        GateVerdict.NEEDS_REVIEW,
    }


def test_case_evaluation_and_metrics_are_derived_from_static_output(
    tmp_path: Path,
    r002_manifest_payload: dict[str, object],
) -> None:
    (
        manifest,
        criteria,
        cache,
        universe,
        labels,
        case,
        criterion_case,
        row,
        parsed,
        verified,
    ) = _first_case_inputs(tmp_path, r002_manifest_payload)
    bundle = build_r002_review(
        case=case,
        row=row,
        criterion_case=criterion_case,
        parsed=parsed,
    )
    label_by_key = {label.key: label for label in labels.labels}
    result = evaluate_r002_case(
        case=case,
        bundle=bundle,
        verified=verified,
        label_by_key=label_by_key,
        expected_missing=labels.expected_missing,
    )

    assert result.gate_verdict is GateVerdict.BLOCKED
    assert result.gate_reason_codes == ("blocking_criteria",)
    assert result.check_state is CheckState.UNAVAILABLE
    assert result.ci_reason_code is CIReasonCode.NO_OBSERVATIONS
    assert result.runtime_evidence_count == 0
    assert result.resolution_count == 0
    assert result.final_acceptance is False
    assert {item.reason_code for item in result.missing_explanations} == {
        "scopeproof_finding_explicit_gap"
    }

    results = []
    parsed_by_case = {}
    for current_case, current_criteria, cached in zip(
        manifest.cases,
        criteria.cases,
        cache.load_index().cases,
        strict=True,
    ):
        current_row = cache.read_model(
            f"rows/{current_case.row_sha256}",
            SWEbenchVerifiedRow,
        )
        current_parsed = parse_case_diffs(
            case_id=current_case.case_id,
            patch=current_row.patch,
            test_patch=current_row.test_patch,
        )
        current_verified = R002VerifiedCaseLines(
            case_id=current_case.case_id,
            head_sha=current_case.verified_pr_head_sha,
            lines=cached.verified_lines,
        )
        results.append(
            evaluate_r002_case(
                case=current_case,
                bundle=build_r002_review(
                    case=current_case,
                    row=current_row,
                    criterion_case=current_criteria,
                    parsed=current_parsed,
                ),
                verified=current_verified,
                label_by_key=label_by_key,
                expected_missing=labels.expected_missing,
            )
        )
        parsed_by_case[current_case.case_id] = current_parsed
    metrics = calculate_metrics(results, universe, labels, parsed_by_case)
    assert metrics.owner_confirmed_label_candidate_precision == metric(0, 0)
    assert metrics.criterion_candidate_coverage == metric(0, 20)
    assert metrics.candidate_to_gold_file_coverage == metric(0, 20)
    assert metrics.candidate_to_gold_hunk_coverage == metric(0, 20)
    assert metrics.missing_evidence_explanation_completeness == metric(60, 60)


def test_metric_zero_denominator_is_not_applicable() -> None:
    assert metric(0, 0) == R002Metric(
        state=R002MetricState.NOT_APPLICABLE,
        numerator=0,
        denominator=0,
        value=None,
    )


def test_evaluate_maps_retrieved_candidate_through_verified_head(
    tmp_path: Path,
    r002_manifest_payload: dict[str, object],
) -> None:
    (
        _manifest,
        _criteria,
        _cache,
        universe,
        labels,
        case,
        criterion_case,
        row,
        parsed,
        verified,
    ) = _first_case_inputs(tmp_path, r002_manifest_payload)
    criterion = criterion_case.criteria[0].model_copy(
        update={"text": "new-1"},
    )
    matching_criteria = criterion_case.model_copy(
        update={"criteria": (criterion,)},
    )
    bundle = build_r002_review(
        case=case,
        row=row,
        criterion_case=matching_criteria,
        parsed=parsed,
    )

    result = evaluate_r002_case(
        case=case,
        bundle=bundle,
        verified=verified,
        label_by_key={label.key: label for label in labels.labels},
        expected_missing=(),
    )

    assert len(result.retrieved_candidates) == 1
    assert result.retrieved_candidates[0].key in universe.candidate_keys
    assert result.retrieved_candidates[0].owner_label_relevant is True


def test_missing_explanation_derivation_covers_all_fail_closed_shapes(
    tmp_path: Path,
    r002_manifest_payload: dict[str, object],
) -> None:
    (
        _manifest,
        _criteria,
        _cache,
        _universe,
        labels,
        case,
        criterion_case,
        row,
        parsed,
        _verified,
    ) = _first_case_inputs(tmp_path, r002_manifest_payload)
    bundle = build_r002_review(
        case=case,
        row=row,
        criterion_case=criterion_case,
        parsed=parsed,
    )
    expected = labels.expected_missing[0]
    finding = bundle.findings[0].model_copy(
        update={
            "status": FindingStatus.EVIDENCE_FOUND,
            "missing_evidence": (),
        }
    )
    no_candidate = _build_missing_explanations(
        case=case,
        findings=(finding,),
        retrieved=(),
        expected_missing=(expected,),
    )
    assert no_candidate[0].reason_code == "no_candidate_retrieved_for_type"

    irrelevant = SimpleNamespace(
        key=SimpleNamespace(criterion_id=expected.criterion_id),
        evidence_type=expected.evidence_type,
        owner_label_relevant=False,
    )
    irrelevant_only = _build_missing_explanations(
        case=case,
        findings=(finding,),
        retrieved=(irrelevant,),
        expected_missing=(expected,),
    )
    assert irrelevant_only[0].reason_code == "retrieved_only_owner_labelled_irrelevant"

    relevant = SimpleNamespace(
        key=SimpleNamespace(criterion_id=expected.criterion_id),
        evidence_type=expected.evidence_type,
        owner_label_relevant=True,
    )
    with pytest.raises(R002RunError, match="expected_missing_label_conflict"):
        _build_missing_explanations(
            case=case,
            findings=(finding,),
            retrieved=(relevant,),
            expected_missing=(expected,),
        )
    with pytest.raises(R002RunError, match="benchmark_gate_failed"):
        _build_missing_explanations(
            case=case,
            findings=(finding, finding),
            retrieved=(),
            expected_missing=(expected,),
        )
    assert (
        _build_missing_explanations(
            case=case,
            findings=(),
            retrieved=(),
            expected_missing=(expected,),
        )
        == ()
    )


def _complete_run_inputs(
    tmp_path: Path,
    payload: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
):
    manifest, criteria, cache = _prepared_annotation_inputs(tmp_path, payload)
    universe = r002_runner.build_annotation_universe(
        manifest=manifest,
        criteria=criteria,
        cache=cache,
    )
    labels = _labels_for_universe(criteria, universe, confirmed=True)
    monkeypatch.setattr(r002_runner, "load_source_manifest", lambda _path: manifest)
    monkeypatch.setattr(
        r002_runner,
        "load_confirmed_criteria",
        lambda _path, _manifest_hash: criteria,
    )
    monkeypatch.setattr(
        r002_runner,
        "load_confirmed_labels",
        lambda _path, _manifest_hash, _criteria_hash: labels,
    )
    return manifest, criteria, cache, universe, labels


def test_run_r002_executes_all_cases_twice_without_partial_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
) -> None:
    _manifest, _criteria, _cache, universe, _labels = _complete_run_inputs(
        tmp_path,
        r002_manifest_payload,
        monkeypatch,
    )
    result = run_r002(
        manifest_path=tmp_path / "source_manifest.json",
        criteria_path=tmp_path / "criteria.json",
        labels_path=tmp_path / "labels.json",
        cache_root=tmp_path / "cache",
        scopeproof_commit="a" * 40,
    )

    assert result.executed_case_count == 20
    assert result.failed_case_count == 0
    assert result.skipped_case_count == 0
    assert result.annotation_candidate_count == universe.candidate_count
    assert result.normalized_rerun_mismatches == 0
    assert result.hard_gate_errors == ()
    assert len(result.case_results) == 20
    assert all(
        (tmp_path / "cache" / "reviews" / f"{case.case_id}.json").is_file()
        for case in result.case_results
    )


def test_run_r002_rejects_stable_second_pass_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
) -> None:
    _complete_run_inputs(tmp_path, r002_manifest_payload, monkeypatch)
    execute = r002_runner._execute_r002_pass
    calls = 0

    def mismatching_pass(**kwargs):
        nonlocal calls
        calls += 1
        result = execute(**kwargs)
        if calls == 2:
            return result.model_copy(update={"scopeproof_commit": "b" * 40})
        return result

    monkeypatch.setattr(r002_runner, "_execute_r002_pass", mismatching_pass)
    with pytest.raises(R002RunError, match="normalized_rerun_mismatch"):
        run_r002(
            manifest_path=tmp_path / "source_manifest.json",
            criteria_path=tmp_path / "criteria.json",
            labels_path=tmp_path / "labels.json",
            cache_root=tmp_path / "cache",
            scopeproof_commit="a" * 40,
        )
    assert calls == 2


def test_run_r002_aborts_on_one_cache_input_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
) -> None:
    manifest, _criteria, cache, _universe, _labels = _complete_run_inputs(
        tmp_path,
        r002_manifest_payload,
        monkeypatch,
    )
    original = cache.read_model

    def drift_one(relative_name, model, **kwargs):
        value = original(relative_name, model, **kwargs)
        if relative_name == f"rows/{manifest.cases[0].row_sha256}":
            return value.model_copy(update={"patch": value.patch + "\n"})
        return value

    monkeypatch.setattr(cache, "read_model", drift_one)
    monkeypatch.setattr(r002_runner, "R002Cache", lambda _root: cache)

    with pytest.raises(R002RunError, match="run_input_drift"):
        run_r002(
            manifest_path=tmp_path / "source_manifest.json",
            criteria_path=tmp_path / "criteria.json",
            labels_path=tmp_path / "labels.json",
            cache_root=tmp_path / "cache",
            scopeproof_commit="a" * 40,
        )


def test_prepared_run_rejects_index_case_and_parsed_identity_drift(
    tmp_path: Path,
    r002_manifest_payload: dict[str, object],
) -> None:
    manifest, criteria, cache = _prepared_annotation_inputs(
        tmp_path,
        r002_manifest_payload,
    )
    index = cache.load_index()

    for drifted_index, drifted_criteria in (
        (
            index.model_copy(update={"source_sha256": "f" * 64}),
            criteria,
        ),
        (
            index,
            criteria.model_copy(
                update={
                    "cases": (
                        criteria.cases[0].model_copy(update={"case_id": "R002-002"}),
                        *criteria.cases[1:],
                    )
                }
            ),
        ),
        (
            index.model_copy(
                update={
                    "cases": (
                        index.cases[0].model_copy(update={"parsed_case_sha256": "f" * 64}),
                        *index.cases[1:],
                    )
                }
            ),
            criteria,
        ),
    ):
        original = cache.load_index
        cache.load_index = lambda value=drifted_index: value  # type: ignore[method-assign]
        with pytest.raises(R002RunError, match="run_input_drift"):
            _prepare_run_cases(
                manifest=manifest,
                criteria=drifted_criteria,
                cache=cache,
            )
        cache.load_index = original  # type: ignore[method-assign]


def test_run_r002_maps_unexpected_failures_and_hard_gate_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
) -> None:
    _complete_run_inputs(tmp_path, r002_manifest_payload, monkeypatch)
    monkeypatch.setattr(
        r002_runner,
        "_hard_gate_codes",
        lambda *_args: ("forced_gate_failure",),
    )
    with pytest.raises(R002RunError, match="benchmark_gate_failed"):
        run_r002(
            manifest_path=tmp_path / "source_manifest.json",
            criteria_path=tmp_path / "criteria.json",
            labels_path=tmp_path / "labels.json",
            cache_root=tmp_path / "cache",
            scopeproof_commit="a" * 40,
        )

    monkeypatch.setattr(
        r002_runner,
        "load_source_manifest",
        lambda _path: (_ for _ in ()).throw(RuntimeError("unexpected")),
    )
    with pytest.raises(R002RunError, match="run_input_drift"):
        run_r002(
            manifest_path=tmp_path / "source_manifest.json",
            criteria_path=tmp_path / "criteria.json",
            labels_path=tmp_path / "labels.json",
            cache_root=tmp_path / "cache",
            scopeproof_commit="a" * 40,
        )


def test_run_r002_rejects_annotation_universe_hash_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
) -> None:
    _manifest, _criteria, cache, _universe, _labels = _complete_run_inputs(
        tmp_path,
        r002_manifest_payload,
        monkeypatch,
    )
    original = cache.read_model

    def drift_universe(relative_name, model, **kwargs):
        value = original(relative_name, model, **kwargs)
        if relative_name == "annotation-universe.json":
            return value.model_copy(update={"criteria_set_sha256": "f" * 64})
        return value

    monkeypatch.setattr(cache, "read_model", drift_universe)
    monkeypatch.setattr(r002_runner, "R002Cache", lambda _root: cache)
    with pytest.raises(R002RunError, match="run_input_drift"):
        run_r002(
            manifest_path=tmp_path / "source_manifest.json",
            criteria_path=tmp_path / "criteria.json",
            labels_path=tmp_path / "labels.json",
            cache_root=tmp_path / "cache",
            scopeproof_commit="a" * 40,
        )


def test_redaction_audit_accepts_redacted_result_and_rejects_raw_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
) -> None:
    manifest, _criteria, cache, _universe, _labels = _complete_run_inputs(
        tmp_path,
        r002_manifest_payload,
        monkeypatch,
    )
    result = run_r002(
        manifest_path=tmp_path / "source_manifest.json",
        criteria_path=tmp_path / "criteria.json",
        labels_path=tmp_path / "labels.json",
        cache_root=tmp_path / "cache",
        scopeproof_commit="a" * 40,
    )
    safe = tmp_path / "result.json"
    safe.write_text(result.model_dump_json(), encoding="utf-8")
    audit = audit_r002_redaction(
        cache_root=tmp_path / "cache",
        candidate_paths=(safe, safe),
    )
    assert audit.passed is True
    assert audit.tracked_file_count == 1
    assert audit.raw_value_count == len(audit.checked_value_sha256)

    row = cache.read_model(
        f"rows/{manifest.cases[0].row_sha256}",
        SWEbenchVerifiedRow,
    )
    leaked = tmp_path / "leaked.json"
    leaked.write_text(
        json.dumps({"summary": row.problem_statement}),
        encoding="utf-8",
    )
    with pytest.raises(R002RunError, match="redaction_boundary_failed"):
        audit_r002_redaction(
            cache_root=tmp_path / "cache",
            candidate_paths=(leaked,),
        )


def test_redaction_audit_rejects_symlink_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
) -> None:
    _complete_run_inputs(tmp_path, r002_manifest_payload, monkeypatch)
    target = tmp_path / "target.md"
    target.write_text("safe", encoding="utf-8")
    candidate = tmp_path / "candidate.md"
    candidate.symlink_to(target)

    with pytest.raises(R002RunError, match="redaction_boundary_failed"):
        audit_r002_redaction(
            cache_root=tmp_path / "cache",
            candidate_paths=(candidate,),
        )


def test_redaction_audit_handles_large_safe_text_without_substring_false_positive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
) -> None:
    _manifest, _criteria, cache, _universe, _labels = _complete_run_inputs(
        tmp_path,
        r002_manifest_payload,
        monkeypatch,
    )
    run_r002(
        manifest_path=tmp_path / "source_manifest.json",
        criteria_path=tmp_path / "criteria.json",
        labels_path=tmp_path / "labels.json",
        cache_root=tmp_path / "cache",
        scopeproof_commit="a" * 40,
    )
    safe = tmp_path / "large.md"
    safe.write_text(
        "# Redacted benchmark\n\n"
        "`tests/test_relational.py`\n\n" + ("deterministic engineering evidence\n" * 270_000),
        encoding="utf-8",
    )

    audit = audit_r002_redaction(
        cache_root=tmp_path / "cache",
        candidate_paths=(safe,),
    )

    assert safe.stat().st_size > 8 * 1024 * 1024
    assert audit.tracked_file_count == 1
    assert cache.load_index().cases


def test_redaction_audit_rejects_markdown_body_and_timestamp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
) -> None:
    manifest, _criteria, cache, _universe, _labels = _complete_run_inputs(
        tmp_path,
        r002_manifest_payload,
        monkeypatch,
    )
    run_r002(
        manifest_path=tmp_path / "source_manifest.json",
        criteria_path=tmp_path / "criteria.json",
        labels_path=tmp_path / "labels.json",
        cache_root=tmp_path / "cache",
        scopeproof_commit="a" * 40,
    )
    row = cache.read_model(
        f"rows/{manifest.cases[0].row_sha256}",
        SWEbenchVerifiedRow,
    )
    leaked_body = tmp_path / "body.md"
    leaked_body.write_text(f"> {row.problem_statement}\n", encoding="utf-8")
    with pytest.raises(R002RunError, match="redaction_boundary_failed"):
        audit_r002_redaction(
            cache_root=tmp_path / "cache",
            candidate_paths=(leaked_body,),
        )

    leaked_time = tmp_path / "time.md"
    leaked_time.write_text(
        "generated: 2026-07-24T12:34:56Z\n",
        encoding="utf-8",
    )
    with pytest.raises(R002RunError, match="redaction_boundary_failed"):
        audit_r002_redaction(
            cache_root=tmp_path / "cache",
            candidate_paths=(leaked_time,),
        )


@pytest.mark.parametrize(
    "payload",
    (
        b"\xff",
        b"{",
        b'{"problem_statement":"redacted"}',
        b'{"summary":"etag: secret"}',
        b'{"summary":"550e8400-e29b-41d4-a716-446655440000"}',
    ),
)
def test_redaction_audit_fails_closed_for_invalid_or_forbidden_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
    payload: bytes,
) -> None:
    _complete_run_inputs(tmp_path, r002_manifest_payload, monkeypatch)
    run_r002(
        manifest_path=tmp_path / "source_manifest.json",
        criteria_path=tmp_path / "criteria.json",
        labels_path=tmp_path / "labels.json",
        cache_root=tmp_path / "cache",
        scopeproof_commit="a" * 40,
    )
    candidate = tmp_path / "candidate.json"
    candidate.write_bytes(payload)
    with pytest.raises(R002RunError, match="redaction_boundary_failed"):
        audit_r002_redaction(
            cache_root=tmp_path / "cache",
            candidate_paths=(candidate,),
        )


def test_redaction_audit_rejects_empty_missing_and_nonregular_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
) -> None:
    _complete_run_inputs(tmp_path, r002_manifest_payload, monkeypatch)
    run_r002(
        manifest_path=tmp_path / "source_manifest.json",
        criteria_path=tmp_path / "criteria.json",
        labels_path=tmp_path / "labels.json",
        cache_root=tmp_path / "cache",
        scopeproof_commit="a" * 40,
    )
    for candidates in (
        (),
        (tmp_path / "missing.json",),
        (tmp_path,),
    ):
        with pytest.raises(R002RunError, match="redaction_boundary_failed"):
            audit_r002_redaction(
                cache_root=tmp_path / "cache",
                candidate_paths=candidates,
            )


def test_redaction_list_decoder_and_hard_gate_codes_fail_closed() -> None:
    assert R002RunError.allowed_reason_codes == {
        "run_input_drift",
        "reannotation_required",
        "expected_missing_label_conflict",
        "redaction_boundary_failed",
        "normalized_rerun_mismatch",
        "benchmark_gate_failed",
        "scopeproof_commit_required_outside_checkout",
        "scopeproof_git_probe_failed",
        "scopeproof_checkout_dirty",
        "scopeproof_head_invalid",
        "scopeproof_commit_mismatch",
    }
    assert _decoded_json_list('["test_one", ""]') == ("test_one",)
    for invalid in ("not-json", "{}", "[1]"):
        with pytest.raises(R002RunError, match="redaction_boundary_failed"):
            _decoded_json_list(invalid)

    invalid_case = SimpleNamespace(
        check_state=CheckState.PASSING,
        ci_reason_code=CIReasonCode.NO_OBSERVATIONS,
        runtime_evidence_count=1,
        resolution_count=1,
        final_acceptance=True,
        separation_errors=1,
        reference_errors=1,
        missing_explanations=(),
        gate_verdict=GateVerdict.READY,
    )
    invalid_metrics = SimpleNamespace(
        implementation_test_separation_errors=1,
        immutable_reference_integrity_errors=1,
        parse_errors=1,
        schema_errors=1,
        source_hash_errors=1,
        source_sha_errors=1,
        unexpected_ready_count=1,
        normalized_rerun_mismatches=1,
    )
    labels = SimpleNamespace(
        expected_missing=(
            SimpleNamespace(
                case_id="R002-001",
                criterion_id="AC-01",
                evidence_type="test",
            ),
        )
    )
    assert _hard_gate_codes((invalid_case,), invalid_metrics, labels) == (
        "case_count_invalid",
        "integrity_error",
        "missing_explanation_incomplete",
        "rerun_mismatch",
        "static_research_boundary_invalid",
        "unexpected_ready",
    )
