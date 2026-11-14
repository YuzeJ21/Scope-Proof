"""Constructed CI manifest display in the local workbench."""

import json

import pytest
from streamlit.testing.v1 import AppTest

from scopeproof_core.reviews.ci_status import MAX_CI_STATUS_BYTES
from scopeproof_core.schemas.models import normalized_criteria_sha256
from tests.junit_audit_fixture import junit_audit_state


def _panel(available: bool = True, exact_head: bool = True) -> None:
    from apps.web.ci_status import render_criterion_ci_status
    from tests.junit_audit_fixture import junit_audit_state

    bundle = junit_audit_state().bundle
    assert bundle is not None
    if not exact_head:
        bundle = bundle.model_copy(update={
            "review": bundle.review.model_copy(update={"head_sha": "legacy-head"}),
        })
    render_criterion_ci_status(bundle, available=available)


@pytest.fixture
def manifest_payload() -> dict:
    bundle = junit_audit_state().bundle
    assert bundle is not None
    return {
        "schema_version": "criterion-ci-status-v1",
        "repository": bundle.review.repository,
        "pr_number": bundle.review.pr_number,
        "criteria_sha256": normalized_criteria_sha256(bundle.criteria),
        "expected_tests": {"AC-01": ["export_rows"], "AC-02": ["row_access"]},
        "runs": [
            {
                "run_id": "previous",
                "head_sha": "b" * 40,
                "source_url": "https://ci.example.invalid/runs/previous",
                "outcomes": {"row_access": "passed"},
            },
            {
                "run_id": "current",
                "head_sha": bundle.review.head_sha,
                "source_url": "https://ci.example.invalid/runs/current",
                "outcomes": {"export_rows": "failed", "row_access": "skipped"},
            },
        ],
    }


def _upload(app: AppTest, payload: bytes) -> AppTest:
    return app.file_uploader[0].set_value(("ci-status.json", payload, "application/json")).run()


def _statuses(app: AppTest) -> list[dict]:
    assert not app.exception
    return app.table[0].value.to_dict(orient="records")


def test_ci_display_uses_current_manifest_and_shows_explicit_run_source(
    manifest_payload: dict,
) -> None:
    app = AppTest.from_function(_panel).run()
    assert not app.exception
    assert "Reviewed pull request · constructed/audit-example #17" in [
        node.value for node in app.text
    ]
    assert _statuses(app) == [
        {"Criterion": "AC-01", "CI status": "Unknown"},
        {"Criterion": "AC-02", "CI status": "Unknown"},
    ]
    app = _upload(app, json.dumps(manifest_payload).encode())
    assert _statuses(app) == [
        {"Criterion": "AC-01", "CI status": "Failed"},
        {"Criterion": "AC-02", "CI status": "Explicitly skipped"},
    ]
    app.selectbox[0].select("AC-02").run()
    detail = app.dataframe[0].value.to_dict(orient="records")
    assert len(detail) == 1
    assert detail[0]["Expected test"] == "row_access"
    assert detail[0]["CI status"] == "Explicitly skipped"
    assert detail[0]["CI runs"] == "current"
    assert detail[0]["Why"]
    assert [entry.value for entry in app.text if entry.value.startswith("CI run ")] == [
        "CI run current · " + "a" * 40,
    ]
    assert any("](<https://ci.example.invalid/runs/current>)" in node.value
               for node in app.markdown)


@pytest.mark.parametrize("failure", ["malformed", "different_criteria", "over_limit"])
def test_invalid_upload_leaves_all_statuses_unknown(
    failure: str, manifest_payload: dict,
) -> None:
    app = AppTest.from_function(_panel).run()
    app = _upload(app, json.dumps(manifest_payload).encode())
    assert _statuses(app)[0]["CI status"] == "Failed"
    if failure == "malformed":
        bad_payload = b"{"
    elif failure == "different_criteria":
        manifest_payload["criteria_sha256"] = "f" * 64
        bad_payload = json.dumps(manifest_payload).encode()
    else:
        bad_payload = json.dumps(manifest_payload).encode().ljust(MAX_CI_STATUS_BYTES + 1)
    app = _upload(app, bad_payload)
    assert [row["CI status"] for row in _statuses(app)] == ["Unknown", "Unknown"]
    assert len(app.error) == 1
    assert not app.selectbox


@pytest.mark.parametrize(("available", "exact_head"), [(False, True), (True, False)])
def test_ci_display_has_no_upload_against_conflict_or_legacy_head(
    available: bool, exact_head: bool,
) -> None:
    app = AppTest.from_function(_panel, args=(available, exact_head)).run()
    assert not app.exception
    assert not app.file_uploader
    assert not app.table
