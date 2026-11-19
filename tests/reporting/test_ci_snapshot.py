"""Verify the standalone CI handoff without changing the review or its evidence."""

import json
from hashlib import sha256

import pytest

from scopeproof_core.reporting.ci_snapshot import (
    build_ci_status_snapshot,
    export_ci_status_snapshot_html,
)
from scopeproof_core.reporting.exporters import export_html
from scopeproof_core.reviews.ci_status import load_ci_status_manifest
from scopeproof_core.schemas.models import normalized_criteria_sha256
from tests.junit_audit_fixture import junit_audit_state

HEAD = "a" * 40
OLD_HEAD = "c" * 40


def _run(run_id, head, **outcomes):
    return {
        "run_id": run_id,
        "head_sha": head,
        "source_url": f"https://ci.example.invalid/runs/{run_id}",
        "outcomes": outcomes,
    }


@pytest.fixture
def state():
    return junit_audit_state()


@pytest.fixture
def manifest_data(state):
    return {
        "schema_version": "criterion-ci-status-v1",
        "repository": state.review.repository,
        "pr_number": state.review.pr_number,
        "criteria_sha256": normalized_criteria_sha256(state.bundle.criteria),
        "expected_tests": {"AC-01": ["filter", "format", "access", "missing"]},
        "runs": [
            _run("old", OLD_HEAD, format="passed"),
            _run("initial", HEAD, filter="failed", access="skipped"),
        ],
    }


def _build(bundle, data, *, source="manual-upload", fingerprint=None):
    payload = json.dumps(data).encode()
    return build_ci_status_snapshot(
        bundle, load_ci_status_manifest(payload),
        manifest_sha256=sha256(payload).hexdigest() if fingerprint is None else fingerprint,
        source=source,
    )


def test_snapshot_includes_all_criteria_and_distinguishes_stale_skipped_missing(
    state, manifest_data,
):
    original = state.model_dump_json()
    acceptance_html = export_html(state)
    snapshot = _build(state.bundle, manifest_data)
    rendered = export_ci_status_snapshot_html(snapshot)

    assert "<title>ScopeProof CI Status Snapshot</title>" in rendered
    assert "Externally supplied CI results." in rendered
    assert "This snapshot does not record an acceptance decision." in rendered
    for value in (
        state.review.review_id,
        state.review.repository,
        HEAD,
        manifest_data["criteria_sha256"],
        sha256(json.dumps(manifest_data).encode()).hexdigest(),
        "Manual upload",
        "CONSTRUCTED export behavior",
        "CONSTRUCTED failure behavior",
        "CI reports failure for the reviewed build.",
        "CI reports a result for a different build.",
        "CI explicitly skipped this test on this build.",
        "The manifest supplies no result or explicit skip.",
        "The manifest does not identify expected tests for this criterion.",
    ):
        assert value in rendered
    assert rendered.count('href="https://ci.example.invalid/runs/initial"') == 1
    assert rendered.count('href="https://ci.example.invalid/runs/old"') == 1
    assert OLD_HEAD in rendered
    assert state.model_dump_json() == original
    assert export_html(state) == acceptance_html


def test_snapshot_cites_both_conflicting_exact_head_runs(state, manifest_data):
    manifest_data["runs"].extend([
        _run("rerun", HEAD, filter="passed"),
        _run("irrelevant", HEAD),
    ])
    snapshot = _build(state.bundle, manifest_data, source="configured-local")
    rendered = export_ci_status_snapshot_html(snapshot)

    assert "Exact-build results conflict." in rendered
    assert "Configured local folder" in rendered
    assert 'href="https://ci.example.invalid/runs/initial"' in rendered
    assert 'href="https://ci.example.invalid/runs/rerun"' in rendered
    assert "irrelevant" not in rendered


def test_snapshot_escapes_criterion_text_and_run_url(state, manifest_data):
    criterion, other = state.bundle.criteria
    changed = criterion.model_copy(update={"text": '<img src="outside" onerror="oops"> &'})
    digest = normalized_criteria_sha256([changed, other])
    provenance = state.review.criteria_source_provenance.model_copy(
        update={"normalized_criteria_sha256": digest},
    )
    bundle = state.bundle.model_copy(update={
        "criteria": [changed, other],
        "review": state.review.model_copy(update={"criteria_source_provenance": provenance}),
    })
    manifest_data["criteria_sha256"] = digest
    manifest_data["runs"][1]["source_url"] = (
        'https://ci.example.invalid/runs/match?branch="release"&result=ok'
    )

    rendered = export_ci_status_snapshot_html(_build(bundle, manifest_data))

    assert "&lt;img src=&quot;outside&quot; onerror=&quot;oops&quot;&gt; &amp;" in rendered
    assert "<img" not in rendered
    assert "<script" not in rendered
    assert (
        'href="https://ci.example.invalid/runs/match?branch=&quot;release&quot;&amp;result=ok"'
        in rendered
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository", "other/repository"),
        ("pr_number", 18),
        ("criteria_sha256", "d" * 64),
    ],
)
def test_snapshot_rejects_another_review_context(state, manifest_data, field, value):
    manifest_data[field] = value
    with pytest.raises(ValueError, match="review context"):
        _build(state.bundle, manifest_data)


def test_snapshot_rejects_stale_only_manifest(state, manifest_data):
    manifest_data["runs"] = [_run("old", OLD_HEAD, filter="passed")]
    with pytest.raises(ValueError, match="exact-head run"):
        _build(state.bundle, manifest_data)


@pytest.mark.parametrize("updates", [{"criteria_confirmed": False}, {"head_sha": "short"}])
def test_snapshot_rejects_unconfirmed_or_inexact_review(state, manifest_data, updates):
    bundle = state.bundle.model_copy(update={"review": state.review.model_copy(update=updates)})
    with pytest.raises(ValueError, match="confirmed criteria and an exact reviewed head"):
        _build(bundle, manifest_data)


def test_snapshot_rejects_invalid_manifest_fingerprint(state, manifest_data):
    with pytest.raises(ValueError, match="manifest_sha256"):
        _build(state.bundle, manifest_data, fingerprint="unknown")


def test_exact_head_without_reported_outcomes_does_not_cite_an_unrelated_run(state, manifest_data):
    manifest_data["runs"] = [_run("empty", HEAD)]

    rendered = export_ci_status_snapshot_html(_build(state.bundle, manifest_data))

    assert "The manifest supplies no result or explicit skip." in rendered
    assert "No CI runs are cited by the displayed results." in rendered
    assert "/runs/empty" not in rendered


@pytest.mark.parametrize("invalid_reference", ["missing", "duplicate", "unsafe"])
def test_html_export_revalidates_citations(state, manifest_data, invalid_reference):
    snapshot = _build(state.bundle, manifest_data)
    first, second = snapshot.cited_runs
    if invalid_reference == "missing":
        snapshot = snapshot.model_copy(update={"cited_runs": (first,)})
    elif invalid_reference == "duplicate":
        snapshot = snapshot.model_copy(update={"cited_runs": (first, first, second)})
    else:
        first.source_url = "javascript:alert(1)"

    with pytest.raises(ValueError, match=r"(CI run|source_url)"):
        export_ci_status_snapshot_html(snapshot)
