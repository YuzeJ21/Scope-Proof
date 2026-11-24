"""Constructed CI metadata exercises the read-only criterion status rules."""

import json

import pytest

from scopeproof_core.reviews import ci_status
from scopeproof_core.reviews.ci_status import (
    MAX_CI_STATUS_BYTES,
    criterion_ci_statuses,
    load_ci_status_manifest,
)
from tests.junit_audit_fixture import junit_audit_state

HEAD = "a" * 40
OTHER = "c" * 40


@pytest.fixture
def bundle():
    return junit_audit_state().bundle


@pytest.fixture
def manifest_data(bundle):
    return {
        "schema_version": "criterion-ci-status-v1",
        "repository": bundle.review.repository,
        "pr_number": bundle.review.pr_number,
        "criteria_sha256": bundle.review.criteria_source_provenance.normalized_criteria_sha256,
        "expected_tests": {"AC-01": ["filter", "format"], "AC-02": ["access"]},
        "runs": [],
    }


def run(run_id, head, **outcomes):
    return {
        "run_id": run_id,
        "head_sha": head,
        "source_url": f"https://ci.example.invalid/runs/{run_id}",
        "outcomes": outcomes,
    }


def statuses(bundle, data):
    return criterion_ci_statuses(bundle, load_ci_status_manifest(json.dumps(data).encode()))


def test_targeted_run_preserves_same_head_pass_and_failure(bundle, manifest_data):
    first = run("initial", HEAD, filter="failed", format="passed", access="skipped")
    previous = run("previous", OTHER, filter="passed", format="passed", access="passed")
    manifest_data["runs"] = [previous, first]
    before = bundle.model_dump_json()
    filter_status, access_status = statuses(bundle, manifest_data)
    assert (filter_status.criterion_id, filter_status.status) == ("AC-01", "failed")
    assert [(item.test_id, item.status, item.run_ids) for item in filter_status.tests] == [
        ("filter", "failed", ("initial",)), ("format", "passed", ("initial",)),
    ]
    assert (access_status.criterion_id, access_status.status) == ("AC-02", "skipped")
    assert access_status.tests[0].run_ids == ("initial",)

    manifest_data["runs"].insert(
        0, run("targeted", HEAD, filter="skipped", format="skipped", access="failed"),
    )
    updated = statuses(bundle, manifest_data)
    assert updated[0] == filter_status
    assert updated[1].status == "failed"
    assert updated[1].tests[0].run_ids == ("targeted",)
    manifest_data["runs"].reverse()
    assert statuses(bundle, manifest_data) == updated
    assert bundle.model_dump_json() == before


def test_stale_missing_and_unmapped_stay_distinct(bundle, manifest_data):
    manifest_data["expected_tests"].pop("AC-02")
    manifest_data["runs"] = [
        run("old", OTHER, filter="passed", format="skipped"),
        run("current", HEAD),
    ]
    mapped, unmapped = statuses(bundle, manifest_data)
    assert mapped.status == "unknown"
    assert [(item.status, item.run_ids) for item in mapped.tests] == [
        ("stale", ("old",)), ("unknown", ()),
    ]
    assert unmapped.status == "unknown"
    assert not unmapped.tests
    assert all(row.status == "unknown" and not row.tests for row in criterion_ci_statuses(bundle))
    manifest_data["runs"][0]["outcomes"]["format"] = "failed"
    assert statuses(bundle, manifest_data)[0].status == "stale"
    manifest_data["runs"] = [run("current", HEAD, filter="passed", format="passed")]
    assert statuses(bundle, manifest_data)[0].status == "passed"
    manifest_data["runs"] = [run("current", HEAD, filter="passed", format="skipped")]
    assert statuses(bundle, manifest_data)[0].status == "skipped"


def test_disagreeing_same_head_outcomes_stay_unknown(bundle, manifest_data):
    manifest_data["runs"] = [
        run("one", HEAD, access="passed"),
        run("two", HEAD, access="failed"),
        run("old", OTHER, access="failed"),
    ]
    check = statuses(bundle, manifest_data)[1].tests[0]
    assert check.status == "unknown"
    assert check.run_ids == ("one", "two")
    assert "conflict" in check.reason.lower()


def test_follow_up_deduplicates_tests_with_their_mapped_criteria(bundle, manifest_data):
    manifest_data["expected_tests"] = {
        "AC-01": ["missing", "shared", "older"],
        "AC-02": ["shared", "skipped", "conflict", "header"],
    }
    manifest_data["runs"] = [
        run("old", OTHER, older="passed"),
        run(
            "initial", HEAD, shared="failed", skipped="skipped", conflict="passed", header="passed",
        ),
        run("targeted", HEAD, conflict="failed"),
    ]
    checks = statuses(bundle, manifest_data)
    follow_up = ci_status.summarize_ci_follow_up(checks)

    assert not follow_up.unmapped_criterion_ids
    assert [(test.status, test.test_id, test.criterion_ids, test.run_ids)
            for test in follow_up.tests] == [
        ("failed", "shared", ("AC-01", "AC-02"), ("initial",)),
        ("skipped", "skipped", ("AC-02",), ("initial",)),
        ("stale", "older", ("AC-01",), ("old",)),
        ("unknown", "conflict", ("AC-02",), ("initial", "targeted")),
        ("unknown", "missing", ("AC-01",), ()),
    ]
    assert "conflict" in follow_up.tests[-2].reason.lower()
    assert "no result" in follow_up.tests[-1].reason.lower()
    assert checks[1].tests[-1].status == "passed"


def test_follow_up_lists_unmapped_criteria_without_inventing_tests(bundle, manifest_data):
    manifest_data["expected_tests"].pop("AC-02")
    manifest_data["runs"] = [run("current", HEAD, filter="passed", format="passed")]
    follow_up = ci_status.summarize_ci_follow_up(statuses(bundle, manifest_data))

    assert follow_up.tests == ()
    assert follow_up.unmapped_criterion_ids == ("AC-02",)


def test_follow_up_rejects_inconsistent_statuses_for_a_shared_test(bundle, manifest_data):
    manifest_data["expected_tests"] = {"AC-01": ["shared"], "AC-02": ["shared"]}
    manifest_data["runs"] = [run("current", HEAD, shared="passed")]
    first, second = statuses(bundle, manifest_data)
    contradictory = second.model_copy(update={
        "tests": (second.tests[0].model_copy(update={"status": "failed"}),),
    })

    with pytest.raises(ValueError, match="inconsistent CI status"):
        ci_status.summarize_ci_follow_up([first, contradictory])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository", "constructed/different"),
        ("pr_number", 18),
        ("criteria_sha256", "d" * 64),
        ("expected_tests", {"AC-03": ["filter"]}),
    ],
)
def test_manifest_cannot_be_used_for_another_review_context(bundle, manifest_data, field, value):
    manifest_data[field] = value
    with pytest.raises(ValueError, match="review context"):
        statuses(bundle, manifest_data)


@pytest.mark.parametrize(
    "payload",
    [b"{", b"\xff", b'{"runs":[],"runs":[]}', b" " * (MAX_CI_STATUS_BYTES + 1)],
)
def test_unusable_manifest_bytes_are_rejected(payload):
    with pytest.raises(ValueError):
        load_ci_status_manifest(payload)


@pytest.mark.parametrize(
    "runs",
    [
        [run("same", HEAD), run("same", OTHER)],
        [run("run", "a", filter="passed")],
        [run("run", HEAD, filt="passed")],
        [run("run", HEAD, filter="not_run")],
        [dict(run("run", HEAD), source_url="https://name@ci.example.invalid/run")],
        [dict(run("run", HEAD), source_url="http://ci.example.invalid/run")],
        [dict(run("run", HEAD), source_url="javascript:alert(1)")],
    ],
)
def test_invalid_run_data_is_rejected(manifest_data, runs):
    manifest_data["runs"] = runs
    with pytest.raises(ValueError):
        load_ci_status_manifest(json.dumps(manifest_data).encode())


def test_duplicate_test_mapping_rejected(manifest_data):
    manifest_data["expected_tests"]["AC-01"] = ["filter", "filter"]
    with pytest.raises(ValueError, match="duplicate expected test"):
        load_ci_status_manifest(json.dumps(manifest_data).encode())


def test_manifest_limits_total_mappings(manifest_data):
    tests = [f"test-{index}" for index in range(512)]
    manifest_data["expected_tests"] = {f"AC-{index:02}": tests for index in range(9)}
    with pytest.raises(ValueError, match="4,096 criterion-to-test mappings"):
        load_ci_status_manifest(json.dumps(manifest_data).encode())


@pytest.mark.parametrize("unbound", [{"criteria_confirmed": False}, {"head_sha": "short"}])
def test_only_a_confirmed_exact_head_can_be_evaluated(bundle, unbound):
    incomplete = bundle.model_copy(update={"review": bundle.review.model_copy(update=unbound)})
    with pytest.raises(ValueError, match="confirmed criteria and an exact reviewed head"):
        criterion_ci_statuses(incomplete)
