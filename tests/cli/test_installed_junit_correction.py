"""One constructed installed-wheel journey: correction, locked race and inert handoffs."""

import copy
import csv
import html
import io
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REVIEW_ID = "constructed-junit-audit-review"
IMPORT_ID = "constructed-junit-import"
CASE_1 = "suite-0001-case-0001"
CASE_2 = "suite-0001-case-0002"
REVIEWER = '=CONSTRUCTED CLI 审计 <img src=x onerror="alert(1)">'
REASON = "=CONSTRUCTED [mapping](javascript:alert(1)) <script>alert(2)</script>"

# Executed only by the selected installed interpreter, outside the checkout.
# All state, actors and runtime records are constructed fixtures.
SEED_CODE = """
from pathlib import Path
import runpy
import sys
import apps
import scopeproof_core
from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.lifecycle import append_external_verification, append_resolution
from scopeproof_core.schemas.models import EvidenceLevel, HumanDecision, ResolutionEvent
from scopeproof_core.schemas.models import ReviewState, RuntimeEvidence
from scopeproof_core.storage.json_store import JsonReviewStore
assert all(Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
           for module in (apps, scopeproof_core))
state = runpy.run_path(sys.argv[1])["junit_audit_state"]()
payload = state.model_dump(mode="python")
payload["analysis_history"] = [state.bundle.model_dump(mode="python")]
payload["criteria_revision"]["number"] = 2
payload["bundle"]["criteria_revision_number"] = 2
payload["bundle"]["junit_evidence_imports"][0]["criteria_revision_number"] = 2
state = validated_review_state(ReviewState.model_validate(payload))
runtime = RuntimeEvidence(
    runtime_evidence_id="constructed-installed-correction-runtime",
    repository=state.review.repository, pr_number=state.review.pr_number,
    head_sha=state.review.head_sha, criterion_id="AC-01",
    artifact_reference="https://example.test/constructed-runtime",
    scenario="CONSTRUCTED installed CLI fixture",
    environment="CONSTRUCTED disposable storage",
    result="CONSTRUCTED data, no genuine verification asserted",
    reviewer="CONSTRUCTED runtime actor", evidence_level=EvidenceLevel.E3,
    limitations=["Automated fixture, no personal testing or qualifying review"],
)
state = append_external_verification(state, runtime, ResolutionEvent(
    criterion_id="AC-01", decision=HumanDecision.MANUALLY_VERIFIED,
    reviewer=runtime.reviewer, comment="CONSTRUCTED paired record",
    claimed_evidence_level=EvidenceLevel.E3, runtime_evidence_id=runtime.runtime_evidence_id,
))
state = append_resolution(state, ResolutionEvent(
    criterion_id="AC-02", decision=HumanDecision.ACCEPTED,
    reviewer="CONSTRUCTED actor", comment="CONSTRUCTED evidence gap acknowledged",
))
state = append_resolution(state, ResolutionEvent(
    final_acceptance=True, reviewer="CONSTRUCTED actor",
    comment="CONSTRUCTED acceptance flag, no qualifying review",
))
JsonReviewStore(Path(sys.argv[2])).save(state)
"""


def installed_command(interpreter, *args):
    return [str(interpreter), "-X", "utf8", "-I", *args]


def run_installed(interpreter, workdir, *args, expected=0):
    result = subprocess.run(
        installed_command(interpreter, *args),
        cwd=workdir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert result.returncode == expected, result.stdout + result.stderr
    return result


def seed_installed(interpreter, workdir):
    recipe = workdir / "constructed_correction_fixture.py"
    shutil.copy2(Path(__file__).parents[1] / "junit_audit_fixture.py", recipe)
    records = workdir / "explicit-constructed-records"
    run_installed(interpreter, workdir, "-c", SEED_CODE, str(recipe), str(records))
    return records, records / f"{REVIEW_ID}.json"


def correction_arguments(records, fingerprint, *, maps=None, confirmed=True):
    if maps is None:
        maps = [("AC-01", CASE_2), ("AC-02", CASE_1)]
    args = [
        "-m",
        "scopeproof_core.cli",
        "correct-junit-mappings",
        REVIEW_ID,
        "--storage-dir",
        str(records),
        "--import-id",
        IMPORT_ID,
        "--reviewer",
        REVIEWER,
        "--reason",
        REASON,
        "--expected-state-fingerprint",
        fingerprint,
    ]
    for criterion, case in maps:
        args.extend(["--map", f"{criterion}={case}"])
    if confirmed:
        args.append("--confirm-whole-import")
    return args


def without_correction_audit(state):
    state = copy.deepcopy(state)
    for key in ("junit_import_events", "effective_junit_mappings", "active_junit_import_ids"):
        state["bundle"].pop(key, None)
    return state


def test_installed_junit_correction_race_restart_and_four_format_handoffs(tmp_path):
    interpreter = os.environ.get("SCOPEPROOF_INSTALLED_PYTHON")
    if not interpreter:
        pytest.skip("set SCOPEPROOF_INSTALLED_PYTHON to an isolated installed-wheel interpreter")
    records, record = seed_installed(interpreter, tmp_path)
    original_bytes = record.read_bytes()
    original = json.loads(original_bytes)["state"]
    assert original["review"]["final_acceptance"] is True
    assert original["bundle"]["runtime_evidence"]
    assert original["analysis_history"]

    def catalog():
        return json.loads(
            run_installed(
                interpreter,
                tmp_path,
                "-m",
                "scopeproof_core.cli",
                "junit-imports",
                REVIEW_ID,
                "--storage-dir",
                str(records),
            ).stdout
        )

    initial_catalog = catalog()
    original_mappings = original["bundle"]["junit_evidence_imports"][0]["criterion_mappings"]
    assert initial_catalog["imports"][0]["original_mappings"] == original_mappings
    assert initial_catalog["imports"][0]["effective_mappings"] == original_mappings
    assert initial_catalog["imports"][0]["mapping_correction_events"] == []
    fingerprint = initial_catalog["state_fingerprint"]
    for changes in (
        {"confirmed": False},
        {"maps": []},
        {"maps": [("AC-01", CASE_1), ("AC-02", CASE_2)]},
    ):
        rejected = run_installed(
            interpreter,
            tmp_path,
            *correction_arguments(records, fingerprint, **changes),
            expected=2,
        )
        assert rejected.stdout == ""
        assert record.read_bytes() == original_bytes

    command = installed_command(interpreter, *correction_arguments(records, fingerprint))
    children = [
        subprocess.Popen(
            command,
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        for _ in range(2)
    ]
    try:
        results = [(child, *child.communicate(timeout=60)) for child in children]
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
    assert sorted(child.returncode for child in children) == [0, 2], results
    receipt = json.loads(next(out for child, out, _ in results if child.returncode == 0))
    failed = next((out, err) for child, out, err in results if child.returncode == 2)
    assert failed[0] == "" and "stale" in failed[1].lower()
    after = json.loads(record.read_bytes())["state"]
    assert without_correction_audit(after) == without_correction_audit(original)
    assert len(after["bundle"]["junit_import_events"]) == 1
    event = after["bundle"]["junit_import_events"][0]
    assert receipt["event"] == event
    valid_bytes = record.read_bytes()
    disguised = json.loads(valid_bytes)
    disguised["record_version"] = 8
    disguised_event = disguised["state"]["bundle"]["junit_import_events"][0]
    disguised_event.pop("action")
    disguised_event.pop("schema_version")
    record.write_text(json.dumps(disguised), encoding="utf-8")
    invalid_bytes = record.read_bytes()
    try:
        rejected = run_installed(
            interpreter, tmp_path, "-m", "scopeproof_core.cli", "junit-imports", REVIEW_ID,
            "--storage-dir", str(records),
            expected=2,
        )
        assert rejected.stdout == ""
        assert record.read_bytes() == invalid_bytes
    finally:
        record.write_bytes(valid_bytes)
    assert event["action"] == "mapping_corrected"
    assert event["reviewer"] == REVIEWER and event["reason"] == REASON
    assert event["previous_correction_event_id"] is None
    assert event["criterion_mappings"] == [
        {"criterion_id": "AC-01", "test_case_ids": [CASE_2]},
        {"criterion_id": "AC-02", "test_case_ids": [CASE_1]},
    ]
    run_installed(
        interpreter,
        tmp_path,
        "-c",
        """
import json, sys
from pydantic import ValidationError
from scopeproof_core.schemas.models import JUnitMappingCorrectionEvent
event = json.loads(sys.argv[1])
assert JUnitMappingCorrectionEvent.model_validate(event).model_dump(mode="json") == event
event["authenticated_approval"] = True
try:
    JUnitMappingCorrectionEvent.model_validate(event)
except ValidationError:
    pass
else:
    raise AssertionError("correction event must reject invented approval fields")
""",
        json.dumps(event, ensure_ascii=False),
    )

    # Every call starts a new isolated process, including this source-free reopen.
    restarted = catalog()
    entry = restarted["imports"][0]
    assert restarted["state_fingerprint"] != fingerprint
    assert entry["mapped_criterion_ids"] == ["AC-01", "AC-02"]
    assert entry["original_mappings"] == original_mappings
    assert entry["effective_mappings"] == event["criterion_mappings"]
    assert entry["mapping_correction_events"] == [event]
    assert entry["status"] == "active"
    saved_bytes = record.read_bytes()
    reports = {
        format_name: run_installed(
            interpreter,
            tmp_path,
            "-m",
            "scopeproof_core.cli",
            "export",
            REVIEW_ID,
            "--storage-dir",
            str(records),
            "--format",
            format_name,
        ).stdout
        for format_name in ("json", "markdown", "html", "csv")
    }
    assert json.loads(reports["json"]) == after
    expected_text = [
        event["event_id"],
        event["schema_version"],
        event["action"],
        IMPORT_ID,
        event["artifact_sha256"],
        event["review_id"],
        event["repository"],
        event["head_sha"],
        event["confirmed_criteria_sha256"],
        event["previous_mapping_sha256"],
        REVIEWER,
        REASON,
        event["occurred_at"].replace("Z", "+00:00"),
        CASE_1,
        CASE_2,
        *[
            value
            for value in event["criteria_source_provenance"].values()
            if isinstance(value, str)
        ],
        *event["evidence_boundary"].values(),
    ]
    for format_name in ("markdown", "html"):
        report = reports[format_name]
        assert '<img src=x onerror="alert(1)">' not in report
        assert "<script>alert(2)</script>" not in report
        if format_name == "markdown":
            assert "[mapping](javascript:alert(1))" not in report
        readable = html.unescape(re.sub(r"\\(.)", r"\1", report))
        for value in expected_text:
            assert value.replace("Z", "+00:00") in readable, (format_name, value)
        assert "original" in readable.lower() and "effective" in readable.lower()
    rows = {row["criterion_id"]: row for row in csv.DictReader(io.StringIO(reports["csv"]))}
    for criterion, case in (("AC-01", CASE_2), ("AC-02", CASE_1)):
        assert [
            item["test_case_id"] for item in json.loads(rows[criterion]["junit_mapped_cases"])
        ] == [case]
        audit = json.loads(rows[criterion]["junit_import_audit"])[0]
        assert audit["original_mappings"] == original_mappings
        assert audit["effective_mappings"] == event["criterion_mappings"]
        assert audit["mapping_correction_events"] == [event]
        assert all(
            not cell.startswith(("=", "+", "-", "@", "\t", "\r"))
            for cell in rows[criterion].values()
        )
    assert record.read_bytes() == saved_bytes

    noop = run_installed(
        interpreter,
        tmp_path,
        *correction_arguments(records, restarted["state_fingerprint"]),
        expected=2,
    )
    assert noop.stdout == "" and record.read_bytes() == saved_bytes
    run_installed(
        interpreter,
        tmp_path,
        "-m",
        "scopeproof_core.cli",
        "withdraw-junit",
        REVIEW_ID,
        "--storage-dir",
        str(records),
        "--import-id",
        IMPORT_ID,
        "--reviewer",
        "CONSTRUCTED terminal actor",
        "--reason",
        "CONSTRUCTED retire import",
        "--expected-state-fingerprint",
        restarted["state_fingerprint"],
    )
    withdrawn_bytes = record.read_bytes()
    withdrawn = catalog()
    assert withdrawn["imports"][0]["status"] == "withdrawn"
    rejected = run_installed(
        interpreter,
        tmp_path,
        *correction_arguments(records, withdrawn["state_fingerprint"], maps=[("AC-01", CASE_1)]),
        expected=2,
    )
    assert rejected.stdout == "" and record.read_bytes() == withdrawn_bytes
