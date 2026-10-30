"""Constructed source-loading races and contradictions cannot regain authority."""

from unittest.mock import patch

import pytest

from apps.web.deferred_exports import DeferredExportUnavailable, deferred_review_export
from scopeproof_core.demo import build_review, load_demo_labels, load_demo_snapshot
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.github.client import GitHubIngestionError
from scopeproof_core.reporting.exporters import export_json
from scopeproof_core.retrieval.engine import retrieve_evidence_with_diagnostics
from scopeproof_core.reviews.lifecycle import append_resolution, new_review_state
from scopeproof_core.reviews.selected_references import selectable_reference_lines
from scopeproof_core.schemas.models import (
    CheckState,
    CIObservation,
    HumanDecision,
    RepositoryVisibility,
    ResolutionEvent,
    RetrievedFile,
    ReviewInputOrigin,
)
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from scopeproof_core.verification.service import build_findings
from tests.apps.test_source_attachment import load_matching, reopen, saved_reference
from tests.reviews.test_selected_references import append


def simulated_live_saved_source():
    """A wholly constructed network response, never a genuine public review or alpha case."""
    snapshot = load_demo_snapshot().model_copy(
        update={
            "repository_visibility": RepositoryVisibility.VERIFIED_PUBLIC,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
        },
        deep=True,
    )
    bundle = build_review(snapshot, load_demo_labels())
    bundle.review.input_origin = ReviewInputOrigin.LIVE_PUBLIC_GITHUB
    bundle.review.repository_visibility = RepositoryVisibility.VERIFIED_PUBLIC
    automatic = RetrievedFile(
        path="src/constructed_automatic.py",
        content=bundle.criteria[0].text,
        commit_sha=snapshot.head_sha,
        retrieval_reason="Constructed automatic source fixture",
    )
    selected_only = RetrievedFile(
        path="src/constructed_selected_only.py",
        content="constructed_explicit_context()",
        commit_sha=snapshot.head_sha,
        retrieval_reason="Constructed selected-only source fixture",
    )
    result = retrieve_evidence_with_diagnostics(
        snapshot, bundle.criteria, unchanged_files=[automatic]
    )
    bundle.evidence = result.evidence
    bundle.retrieval_diagnostics = result.diagnostics
    bundle.findings = build_findings(bundle.criteria, result.evidence, snapshot.ingestion_state)
    bundle.gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, [], bundle.evidence
    )
    state = new_review_state(bundle)
    candidates = [automatic, selected_only]
    selected = next(
        line
        for line in selectable_reference_lines(state, snapshot, candidates)
        if line.file_path == selected_only.path
    )
    state = append(
        state,
        snapshot,
        selected,
        unchanged_files=candidates,
        reviewer="Constructed simulated-network reference reviewer",
    )
    store = JsonReviewStore(default_local_review_directory())
    store.save(state)
    return reopen(state.review.review_id), state, snapshot, candidates, store


def queued_export(app, state, store):
    guard = app.session_state["source_authority_guard"]
    return deferred_review_export(
        state,
        export_json,
        store=store,
        expected_fingerprint=JsonReviewStore.state_fingerprint(state),
        authority_check=lambda: guard.allows(state),
    )


def test_constructed_live_reload_restores_automatic_and_selected_only_unchanged_sources():
    app, state, snapshot, candidates, store = simulated_live_saved_source()
    path = store.directory / f"{state.review.review_id}.json"
    before = path.read_bytes()
    automatic_paths = {e.file_path for e in state.bundle.evidence}
    assert "src/constructed_automatic.py" in automatic_paths
    assert "src/constructed_selected_only.py" not in automatic_paths
    requested = []

    def fetch_candidates(repository, head_sha, paths):
        requested.append((repository, head_sha, list(paths)))
        return candidates

    with (
        patch(
            "apps.web.source_attachment.load_demo_snapshot",
            side_effect=AssertionError("Simulated live origin must use constructed network stubs"),
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request", return_value=snapshot
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
            side_effect=fetch_candidates,
        ),
    ):
        app = app.button(key="load_reviewed_source").click().run()
    assert not app.exception
    assert requested == [
        (
            state.review.repository,
            state.review.head_sha,
            ["src/constructed_automatic.py", "src/constructed_selected_only.py"],
        )
    ]
    assert {f.path for f in app.session_state["candidate_files"]} == {
        "src/constructed_automatic.py",
        "src/constructed_selected_only.py",
    }
    assert app.session_state["review_source_attachment"] is not None
    assert app.session_state["review_state"] == state
    assert app.session_state["source_authority_guard"].allows(state)
    assert path.read_bytes() == before


def test_fresh_failed_ci_blocks_authority_before_candidate_loading_can_hide_observation():
    app, state, snapshot, _, store = simulated_live_saved_source()
    path = store.directory / f"{state.review.review_id}.json"
    before = path.read_bytes()
    export = queued_export(app, state, store)
    assert export()
    snapshot.ci_observation = CIObservation(
        state=CheckState.FAILING,
        total_check_runs=1,
        failing_check_runs=1,
        reason="Constructed fresh CI contradiction",
    )
    snapshot.check_state = CheckState.FAILING
    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request", return_value=snapshot
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
            side_effect=AssertionError("Fresh CI contradiction must be checked first"),
        ),
    ):
        app = app.button(key="load_reviewed_source").click().run()
    assert not app.exception
    assert app.session_state["review_state"] == state
    assert app.session_state["review_source_attachment"] is None
    assert not app.session_state["source_authority_guard"].allows(state)
    assert all(b.disabled for b in app.download_button if b.key.startswith("download_"))
    assert path.read_bytes() == before
    with pytest.raises(DeferredExportUnavailable):
        export()


def test_saved_update_during_network_load_prevents_attachment_without_overwriting_newer_decision():
    app, state, snapshot, candidates, store = simulated_live_saved_source()
    updated = append_resolution(
        state,
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.CHANGE_REQUIRED,
            reviewer="Constructed concurrent saved-state reviewer",
            comment="Keep this decision written while source was loading.",
        ),
    )
    path = store.directory / f"{state.review.review_id}.json"
    concurrent_bytes = []

    def fetch_snapshot(_url):
        store.save(updated)
        concurrent_bytes.append(path.read_bytes())
        return snapshot

    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            side_effect=fetch_snapshot,
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
            return_value=candidates,
        ),
    ):
        app = app.button(key="load_reviewed_source").click().run()
    assert not app.exception
    assert concurrent_bytes
    assert path.read_bytes() == concurrent_bytes[0]
    assert store.load(state.review.review_id) == updated
    assert app.session_state["review_source_attachment"] is None
    assert app.session_state["snapshot"] is None
    assert app.session_state["source_authority_guard"].allows(updated)


def test_transport_failure_without_observed_source_facts_preserves_authority_and_saved_bytes():
    app, state, _, _, store = simulated_live_saved_source()
    path = store.directory / f"{state.review.review_id}.json"
    before = path.read_bytes()
    export = queued_export(app, state, store)
    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            side_effect=GitHubIngestionError("Constructed unavailable transport"),
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
            side_effect=AssertionError("No snapshot was obtained"),
        ),
    ):
        app = app.button(key="load_reviewed_source").click().run()
    assert not app.exception
    assert app.session_state["review_state"] == state
    assert app.session_state["review_source_attachment"] is None
    assert app.session_state["source_authority_guard"].allows(state)
    assert path.read_bytes() == before
    assert all(not b.disabled for b in app.download_button if b.key.startswith("download_"))
    assert export()


@pytest.mark.parametrize("source", ["snapshot", "candidate"])
def test_attached_source_tampering_revokes_current_authority_and_queued_exports(source):
    if source == "snapshot":
        app, state, snapshot = saved_reference()
        store = JsonReviewStore(default_local_review_directory())
        app = load_matching(app, snapshot)
    else:
        app, state, snapshot, candidates, store = simulated_live_saved_source()
        with (
            patch(
                "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
                return_value=snapshot,
            ),
            patch(
                "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
                return_value=candidates,
            ),
        ):
            app = app.button(key="load_reviewed_source").click().run()
    assert not app.exception
    assert app.session_state["review_source_attachment"] is not None
    path = store.directory / f"{state.review.review_id}.json"
    before = path.read_bytes()
    export = queued_export(app, state, store)
    assert export()
    if source == "snapshot":
        app.session_state["snapshot"].files[-1].lines[0].content = "constructed_tampering()"
    else:
        app.session_state["candidate_files"][0].content = "constructed_tampering()"
    app = app.run()
    assert not app.exception
    assert not app.session_state["source_authority_guard"].allows(state)
    assert app.session_state["review_source_attachment"] is None
    assert app.session_state["snapshot"] is None
    assert all(b.disabled for b in app.download_button if b.key.startswith("download_"))
    assert any("Refresh required" in item.value for item in app.markdown)
    assert path.read_bytes() == before
    with pytest.raises(DeferredExportUnavailable):
        export()


@pytest.mark.parametrize("persisted", [True, False])
def test_export_rechecks_authority_if_observation_changes_during_render(tmp_path, persisted):
    from apps.web.source_attachment import SourceAuthorityGuard
    from tests.apps.test_deferred_exports import accepted_review_state

    state = accepted_review_state()
    store = JsonReviewStore(tmp_path / "guarded-export")
    store.save(state)
    original = (store.directory / f"{state.review.review_id}.json").read_bytes()
    guard = SourceAuthorityGuard()

    def renderer(source):
        guard.block(source)
        return export_json(source)

    callback = deferred_review_export(
        state,
        renderer,
        store=store,
        expected_fingerprint=store.state_fingerprint(state) if persisted else None,
        authority_check=lambda: guard.allows(state),
    )
    with pytest.raises(DeferredExportUnavailable):
        callback()
    assert (store.directory / f"{state.review.review_id}.json").read_bytes() == original
