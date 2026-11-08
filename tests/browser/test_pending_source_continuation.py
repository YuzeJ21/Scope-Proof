"""Installed-wheel continuation of a CONSTRUCTED saved criteria revision."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

from tests.browser import test_packaged_workbench as workbench_helpers
from tests.browser.test_packaged_workbench import (
    _capture_browser_failure,
    _installed_workbench_server,
    _route_loopback_only,
    _run,
    _run_and_wait_for_streamlit_rerun,
)
from tests.browser.test_packaged_workbench import installed_wheel as installed_wheel

pytestmark = pytest.mark.browser

REVIEW_ID = "constructed-pending-source-continuation"
CHANGED_CRITERION = "CONSTRUCTED changed requirement: export the research list as JSON"
CONSTRUCTED_ACTOR = "CONSTRUCTED automatic continuation fixture actor"

# Controlled replay of the observed failure predicate, not a claim about the
# precise Streamlit race: ID input reaches the real server, while this test's
# generic script-state observer cannot report that commit. The app and the
# browser's MutationObserver implementation remain untouched.
CONTROLLED_ID_STATUS_LOSS = """() => {
    document.addEventListener("input", event => {
        if (event.target?.getAttribute("aria-label") !== "Review ID") return;
        window.__scopeproofRerunObserver?.disconnect();
        window.__scopeproofRerunObserved = false;
        window.__scopeproofControlledIDLosses =
            (window.__scopeproofControlledIDLosses || 0) + 1;
        const reopen = () => [...document.querySelectorAll("button")].find(
            button => button.textContent.trim() === "Reopen local review");
        window.__scopeproofControlledIDInitiallyDisabled = reopen()?.disabled === true;
        const observer = new MutationObserver(() => {
            if (!reopen() || reopen().disabled ||
                window.__scopeproofControlledIDEnabledWithoutSignal != null) return;
            window.__scopeproofControlledIDEnabledWithoutSignal =
                window.__scopeproofRerunObserved === false;
        });
        observer.observe(document.documentElement, {
            attributes: true, attributeFilter: ["disabled"], childList: true, subtree: true,
        });
        window.__scopeproofControlledIDSemanticObserver = observer;
    }, true);
}"""


def _suppress_only_review_id_status_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    original = workbench_helpers.ARM_STREAMLIT_RERUN_OBSERVER_SCRIPT
    monkeypatch.setattr(
        workbench_helpers,
        "ARM_STREAMLIT_RERUN_OBSERVER_SCRIPT",
        """() => {
        if (document.activeElement?.getAttribute("aria-label") === "Review ID") {
            window.__scopeproofRerunObserver?.disconnect();
            window.__scopeproofRerunObserved = false;
            return;
        }
        return ("""
        + original
        + """)();
    }""",
    )


def _assert_controlled_review_id_signal_loss(page: Page) -> None:
    assert page.evaluate("window.__scopeproofControlledIDLosses === 1")
    assert page.evaluate("window.__scopeproofControlledIDInitiallyDisabled === true")
    assert page.evaluate("window.__scopeproofControlledIDEnabledWithoutSignal === true")


# This is trusted test setup, copied outside the checkout and run by the installed
# interpreter. Source carried by the demo snapshot is data and is never executed.
CONSTRUCTED_RECIPE = '''\
from datetime import UTC, datetime
from pathlib import Path
import sys
import apps
import scopeproof_core
from scopeproof_core.demo import build_demo_review, load_demo_snapshot
from scopeproof_core.reviews.lifecycle import append_external_verification, new_review_state
from scopeproof_core.reviews.selected_references import (
    append_reviewer_selected_reference, selectable_reference_lines,
)
from scopeproof_core.schemas.models import (
    EvidenceLevel, HumanDecision, ResolutionEvent, RuntimeEvidence,
)
from scopeproof_core.storage.json_store import JsonReviewStore

assert all(Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
           for module in (apps, scopeproof_core))
bundle = build_demo_review()
bundle.review.review_id = "constructed-pending-source-continuation"
state = new_review_state(bundle)
snapshot = load_demo_snapshot()
actor = "CONSTRUCTED automatic continuation fixture actor"
state = append_reviewer_selected_reference(
    state, snapshot=snapshot, selected=next(iter(selectable_reference_lines(state, snapshot))),
    criterion_id="AC-01", reviewer=actor,
    rationale="CONSTRUCTED prior static reference; not execution evidence.",
    expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
)
timestamp = datetime.now(UTC)
artifact = "https://example.test/constructed/continuation/runtime"
state = append_external_verification(
    state,
    RuntimeEvidence(
        runtime_evidence_id="constructed-prior-runtime", repository=snapshot.repository,
        pr_number=snapshot.pr_number, head_sha=snapshot.head_sha, criterion_id="AC-01",
        artifact_reference=artifact, scenario="CONSTRUCTED prior CSV scenario",
        timestamp=timestamp, environment="CONSTRUCTED automatic fixture environment",
        result="CONSTRUCTED stored result; no target code execution occurred.",
        reviewer=actor, evidence_level=EvidenceLevel.E3,
        limitations=["CONSTRUCTED fixture; not independent or qualifying user evidence."],
    ),
    ResolutionEvent(
        event_id="constructed-prior-decision", criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED, comment="CONSTRUCTED prior decision.",
        evidence_url=artifact, claimed_evidence_level=EvidenceLevel.E3,
        runtime_evidence_id="constructed-prior-runtime", reviewer=actor, timestamp=timestamp,
    ),
)
JsonReviewStore(Path(sys.argv[1])).save(state)
'''


def _saved_state(record: Path) -> dict:
    return json.loads(record.read_text(encoding="utf-8"))["state"]


def _reopen(page: Page, base_url: str) -> None:
    page.goto(base_url, wait_until="domcontentloaded")
    page.get_by_text("Resume a saved review", exact=True).click()
    _run_and_wait_for_streamlit_rerun(
        page,
        page.get_by_text("Enter a review ID directly", exact=True).click,
    )
    review_id = page.get_by_role("textbox", name="Review ID", exact=True)
    reopen = page.get_by_role("button", name="Reopen local review", exact=True)
    expect(review_id).to_have_value("")
    expect(reopen).to_be_disabled()
    review_id.fill(REVIEW_ID)
    review_id.press("Tab")
    expect(review_id).to_have_value(REVIEW_ID)
    # This server-computed transition proves the ID committed even if the
    # generic DOM script-state observer misses its short-lived rerun signal.
    expect(reopen).to_be_enabled(timeout=10_000)
    _run_and_wait_for_streamlit_rerun(
        page,
        reopen.click,
    )
    expect(
        page.get_by_text(
            "Review reopened from local storage after validation.",
            exact=True,
        )
    ).to_be_visible()
    expect(page.get_by_text("Loaded source", exact=True)).to_have_count(0)


def _download_json(page: Page, destination: Path) -> dict:
    button = page.get_by_role("button", name="Download JSON", exact=True)
    expect(button).to_be_enabled()
    with page.expect_download() as pending_download:
        button.click()
    download = pending_download.value
    assert download.suggested_filename.endswith(".json")
    download.save_as(destination)
    return json.loads(destination.read_text(encoding="utf-8"))


def _assert_fresh_continuation(state: dict, original: dict, pending: dict) -> None:
    assert state["review"]["review_id"] == REVIEW_ID
    assert state["review"]["created_at"] == original["review"]["created_at"]
    assert state["criteria_revision"] == pending["criteria_revision"]
    assert state["criteria_revision"]["number"] == 2
    assert state["analysis_history"] == [original["bundle"]]
    assert state["resolution_events"] == original["resolution_events"]
    active = state["bundle"]
    assert active["criteria_revision_number"] == 2
    assert active["criteria"][0]["text"] == CHANGED_CRITERION
    assert active["review"] == state["review"]
    assert active["review"]["final_acceptance"] is False
    for field in (
        "resolutions", "runtime_evidence", "file_scope_decisions",
        "reviewer_selected_references", "selected_reference_events",
        "junit_evidence_imports", "junit_import_events",
    ):
        assert active[field] == [], field
    assert active["active_reviewer_selected_reference_ids"] == []
    assert active["active_junit_import_ids"] == []
    assert active["effective_junit_mappings"] == {}


@pytest.mark.parametrize(
    "lose_review_id_status_signal", [False, True], ids=["normal", "controlled-status-loss"],
)
def test_installed_wheel_pending_revision_continues_same_review_after_restart(
    tmp_path: Path, installed_wheel: Path, monkeypatch: pytest.MonkeyPatch,
    lose_review_id_status_signal: bool,
) -> None:
    """Reopen, explicitly reconfirm, reload exact demo source, analyze and reopen."""
    runtime = tmp_path / "pending-continuation-runtime"
    home = runtime / "home"
    home.mkdir(parents=True)
    store = home / ".scopeproof" / "reviews"
    record = store / f"{REVIEW_ID}.json"
    recipe = runtime / "constructed-continuation-setup.py"
    recipe.write_text(CONSTRUCTED_RECIPE, encoding="utf-8")
    _run(str(installed_wheel / "bin" / "python"), "-I", str(recipe), str(store), cwd=runtime)
    original = _saved_state(record)
    assert original["criteria_revision"]["number"] == 1
    assert original["bundle"]["reviewer_selected_references"][0]["reviewer"] == CONSTRUCTED_ACTOR
    assert original["bundle"]["runtime_evidence"][0]["reviewer"] == CONSTRUCTED_ACTOR
    assert original["resolution_events"][0]["reviewer"] == CONSTRUCTED_ACTOR
    diagnostics = Path(os.environ.get(
        "SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics"),
    )) / "pending-continuation"
    external_requests: list[str] = []
    browser_errors: list[str] = []
    completed: dict | None = None
    completed_bytes: bytes | None = None
    pending: dict | None = None
    if lose_review_id_status_signal:
        _suppress_only_review_id_status_signal(monkeypatch)

    with sync_playwright() as playwright:
        for generation in range(2):
            with _installed_workbench_server(
                installed_wheel, runtime, home, log_name=f"continuation-{generation}.log",
            ) as (base_url, log_path):
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(viewport={"width": 1280, "height": 900})
                    context.route(
                        "**/*", lambda route: _route_loopback_only(route, external_requests),
                    )
                    page = context.new_page()
                    if lose_review_id_status_signal:
                        page.add_init_script("(" + CONTROLLED_ID_STATUS_LOSS + ")()")
                    page.on("pageerror", lambda error: browser_errors.append(str(error)))
                    with _capture_browser_failure(
                        page, diagnostics / f"generation-{generation}", log_path,
                    ):
                        _reopen(page, base_url)
                        if lose_review_id_status_signal:
                            _assert_controlled_review_id_signal_loss(page)
                        if generation == 0:
                            assert _saved_state(record) == original
                            page.get_by_text("AC-01 · Must Have · E1", exact=True).click()
                            criterion = page.get_by_role("textbox", name="AC-01", exact=True)
                            criterion.fill(CHANGED_CRITERION)
                            _run_and_wait_for_streamlit_rerun(
                                page, lambda target=criterion: target.press("Tab"),
                            )
                            # A draft alone must not revise persisted acceptance criteria.
                            assert _saved_state(record) == original
                            confirmer = page.get_by_role(
                                "textbox", name="Confirmed by", exact=True,
                            )
                            confirmer.fill(CONSTRUCTED_ACTOR)
                            _run_and_wait_for_streamlit_rerun(
                                page, lambda target=confirmer: target.press("Tab"),
                            )
                            _run_and_wait_for_streamlit_rerun(
                                page, page.get_by_role(
                                    "button", name="Apply edits and confirm criteria", exact=True,
                                ).click,
                            )
                            pending = _saved_state(record)
                            assert pending["bundle"] is None
                            assert pending["criteria_revision"]["number"] == 2
                            assert pending["criteria_revision"]["confirmed"] is True
                            assert pending["criteria_revision"]["criteria"][0]["text"] == (
                                CHANGED_CRITERION
                            )
                            assert pending["review"]["review_id"] == REVIEW_ID
                            assert pending["analysis_history"] == [original["bundle"]]
                            assert pending["resolution_events"] == original["resolution_events"]
                            expect(page.get_by_text("Loaded source", exact=True)).to_have_count(0)
                            run_analysis = page.get_by_role(
                                "button", name="Run deterministic analysis", exact=True,
                            )
                            expect(run_analysis).to_be_disabled()
                            load_source = page.get_by_role(
                                "button", name="Load matching reviewed source", exact=True,
                            )
                            # This is the historical regression: confirmed pending revisions
                            # previously could not use the existing matching-source action.
                            expect(load_source).to_be_enabled()
                            _run_and_wait_for_streamlit_rerun(page, load_source.click)
                            expect(page.get_by_text("Loaded source", exact=True)).to_be_visible()
                            assert _saved_state(record) == pending
                            expect(run_analysis).to_be_enabled()
                            _run_and_wait_for_streamlit_rerun(page, run_analysis.click)
                            expect(page.get_by_role(
                                "link", name="Complete — Analysis generated", exact=True,
                            )).to_be_visible()
                            completed = _saved_state(record)
                            _assert_fresh_continuation(completed, original, pending)
                            exported = _download_json(page, runtime / "continued-review.json")
                            assert exported == completed
                            completed_bytes = record.read_bytes()
                            page.screenshot(
                                path=str(runtime / "continued-review.png"), full_page=True,
                            )
                        else:
                            assert completed is not None and completed_bytes is not None
                            assert pending is not None
                            assert record.read_bytes() == completed_bytes
                            resumed = _download_json(page, runtime / "reopened-review.json")
                            assert resumed == completed
                            _assert_fresh_continuation(resumed, original, pending)
                            assert record.read_bytes() == completed_bytes
                            page.screenshot(
                                path=str(runtime / "reopened-review.png"), full_page=True,
                            )
                finally:
                    browser.close()
    assert external_requests == []
    assert browser_errors == []


def test_installed_reopen_does_not_accept_an_enabled_button_as_validation(
    tmp_path: Path,
    installed_wheel: Path,
) -> None:
    """A nonempty ID enables the real control, but an absent record cannot reopen."""
    runtime = tmp_path / "missing-record-runtime"
    home = runtime / "home"
    store = home / ".scopeproof" / "reviews"
    store.mkdir(parents=True)
    external_requests: list[str] = []
    browser_errors: list[str] = []
    with _installed_workbench_server(
        installed_wheel,
        runtime,
        home,
        log_name="missing-record.log",
    ) as (base_url, _), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            context.route(
                "**/*",
                lambda route: _route_loopback_only(route, external_requests),
            )
            page = context.new_page()
            page.on("pageerror", lambda error: browser_errors.append(str(error)))
            with pytest.raises(
                AssertionError,
                match="Review reopened from local storage after validation",
            ):
                _reopen(page, base_url)
            expect(
                page.get_by_text(
                    "No saved review was found for that review ID.",
                    exact=True,
                )
            ).to_be_visible()
            expect(
                page.get_by_text(
                    "Review reopened from local storage after validation.",
                    exact=True,
                )
            ).to_have_count(0)
            assert list(store.glob("*.json")) == []
            page.screenshot(path=str(runtime / "missing-record-rejected.png"), full_page=True)
        finally:
            browser.close()
    assert external_requests == []
    assert browser_errors == []
