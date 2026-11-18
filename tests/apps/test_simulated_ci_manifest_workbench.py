"""Read the simulated pipeline's unedited CI artifacts in the actual workbench."""

import json
import subprocess
import sys
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

from apps.web.launcher import CI_MANIFEST_DIR_ENV, WORKBENCH_STORAGE_ENV
from scopeproof_core.cli import main
from scopeproof_core.schemas.models import PullRequestSnapshot, ReviewInputOrigin
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.apps.test_streamlit_app import APP_PATH, select_saved_review

_ROOT = Path(__file__).resolve().parents[2]


def _reopen(app: AppTest, review_id: str) -> AppTest:
    app = select_saved_review(app, review_id).button(key="reopen_review").click().run()
    assert not app.exception
    assert app.session_state["review_state"].review.review_id == review_id
    return app


def _panel(app: AppTest):
    panel, = (item for item in app.expander if item.label == "CI status by criterion")
    return panel


def _assert_statuses(app: AppTest, expected: tuple[str, str, str]) -> None:
    table, = _panel(app).get("table")
    assert table.value.to_dict(orient="records") == [
        {"Criterion": f"AC-0{index}", "CI status": status}
        for index, status in enumerate(expected, 1)
    ]


def _upload(app: AppTest, manifest: Path) -> AppTest:
    uploader, = _panel(app).get("file_uploader")
    app = uploader.set_value((manifest.name, manifest.read_bytes(), "application/json")).run()
    assert not app.exception
    return app


def _save_simulated_reviews(output: Path, storage: Path, capsys) -> dict[str, str]:
    capsys.readouterr()
    review_ids = {}
    for build in ("A", "B"):
        assert main([
            "review", "--fixture", str(output / f"{build}-fixture.json"),
            "--requirements", str(output / "ticket-requirements.txt"),
            "--criteria", str(output / "criteria.json"),
            "--confirmation", str(output / "confirmation.json"),
            "--storage-dir", str(storage),
        ]) == 0
        review_ids[build] = json.loads(capsys.readouterr().out)["review_id"]
    return review_ids


def _prepare_workbench_reviews(output: Path) -> tuple[Path, dict[str, str]]:
    """Exercise one-command preparation before consuming its actual saved reviews."""
    from scripts.simulate_ci_manifest import SimulatedRun

    result = subprocess.run(
        [sys.executable, "-m", "scripts.simulate_ci_manifest", "--prepare-workbench", str(output)],
        cwd=_ROOT, capture_output=True, text=True, check=False, timeout=60,
    )
    assert result.returncode == 0, f"{result.stderr}\n{result.stdout}"
    storage = output / "reviews"
    store = JsonReviewStore(storage)
    states = {review_id: store.load(review_id) for review_id in store.list_review_ids()}
    assert len(states) == 2
    review_ids = {}
    for build in ("A", "B"):
        fixture = PullRequestSnapshot.model_validate_json(
            (output / f"{build}-fixture.json").read_bytes(),
        )
        matching, = [
            review_id for review_id, state in states.items()
            if (
                state.review.repository, state.review.pr_number,
                state.review.base_sha, state.review.head_sha,
            ) == (fixture.repository, fixture.pr_number, fixture.base_sha, fixture.head_sha)
        ]
        state = states[matching]
        assert state.criteria_revision.confirmed
        assert state.bundle is not None
        assert state.review.input_origin is ReviewInputOrigin.LOCAL_FIXTURE
        provenance = state.review.criteria_source_provenance
        assert provenance is not None
        assert provenance.confirmed_by == "CONSTRUCTED scripted actor"
        assert provenance.source_uri == "https://ticket.example.invalid/EXP-17"
        run = SimulatedRun.model_validate_json((output / f"{build}-ci.json").read_bytes())
        assert (run.label, run.head, run.environment) == (
            build, fixture.head_sha, "synthetic SQLite and Python",
        )
        review_ids[build] = matching
    assert review_ids["A"] != review_ids["B"]
    return storage, review_ids


def _assert_targeted_provenance(app: AppTest, storage: Path, b_review_id: str) -> None:
    inspect, = _panel(app).get("selectbox")
    app = inspect.set_value("AC-02").run()
    assert not app.exception
    panel = _panel(app)
    details, = panel.get("dataframe")
    row, = details.value.to_dict(orient="records")
    assert row["Expected test"] == "row_entitlement"
    assert row["CI runs"] == "B-targeted"
    run_link = "https://ci.example.invalid/builds/B-targeted"
    assert any(f"](<{run_link}>)" in item.value for item in panel.get("markdown"))
    b_state = JsonReviewStore(storage).load(b_review_id)
    assert f"CI run B-targeted · {b_state.review.head_sha}" in [
        item.value for item in panel.get("text")
    ]
    assert app.session_state["review_state"] == b_state


def _refresh_ci_status(app: AppTest) -> AppTest:
    refresh, = (
        button for button in _panel(app).get("button") if button.label == "Refresh CI status"
    )
    app = refresh.click().run()
    assert not app.exception
    return app


def test_simulated_ci_manifests_open_for_both_builds(tmp_path, monkeypatch, capsys):
    from scripts.simulate_ci_manifest import simulate

    monkeypatch.delenv(CI_MANIFEST_DIR_ENV, raising=False)
    output = tmp_path / "simulated-ci"
    simulate(output)
    storage = tmp_path / "reviews"
    monkeypatch.setenv(WORKBENCH_STORAGE_ENV, str(storage))
    review_ids = _save_simulated_reviews(output, storage, capsys)

    saved_records = {path: path.read_bytes() for path in storage.glob("*.json")}
    assert len(saved_records) == 2
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app = _reopen(app, review_ids["A"])
    app = _upload(app, output / "A-scopeproof-manifest.json")
    _assert_statuses(app, ("Passed", "Passed", "Passed"))

    app = _reopen(app, review_ids["B"])
    _assert_statuses(app, ("Unknown", "Unknown", "Unknown"))
    app = _upload(app, output / "B-scopeproof-manifest.json")
    _assert_statuses(app, ("Failed", "Explicitly skipped", "Passed"))
    app = _upload(app, output / "B-targeted-scopeproof-manifest.json")
    _assert_statuses(app, ("Failed", "Failed", "Passed"))

    _assert_targeted_provenance(app, storage, review_ids["B"])
    assert {path: path.read_bytes() for path in storage.glob("*.json")} == saved_records


def test_workbench_reads_simulated_ci_handoff_before_any_upload(tmp_path, monkeypatch):
    from scripts.simulate_ci_manifest import publish_targeted

    initial = tmp_path / "prepared workbench with spaces"
    storage, review_ids = _prepare_workbench_reviews(initial)
    assert not (initial / "B-targeted-scopeproof-manifest.json").exists()
    handoff = (initial / "manifests").resolve()
    monkeypatch.setenv(WORKBENCH_STORAGE_ENV, str(storage))
    monkeypatch.setenv(CI_MANIFEST_DIR_ENV, str(handoff))
    original_get_option = st.get_option
    listener = "0.0.0.0"
    monkeypatch.setattr(
        st, "get_option",
        lambda key: listener if key == "server.address" else original_get_option(key),
    )
    saved_records = {path: path.read_bytes() for path in storage.glob("*.json")}
    assert len(saved_records) == 2

    initial_a = (initial / "A-scopeproof-manifest.json").read_bytes()
    initial_b = (initial / "B-scopeproof-manifest.json").read_bytes()
    a_handoff, = (path for path in handoff.glob("*.json") if path.read_bytes() == initial_a)
    b_handoff, = (path for path in handoff.glob("*.json") if path.read_bytes() == initial_b)

    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app = _reopen(app, review_ids["A"])
    _assert_statuses(app, ("Unknown", "Unknown", "Unknown"))
    assert not any(button.label == "Refresh CI status" for button in _panel(app).get("button"))
    listener = "127.0.0.1"
    app = app.run()
    _assert_statuses(app, ("Passed", "Passed", "Passed"))
    assert "CI source: configured local manifest." in [
        caption.value for caption in _panel(app).get("caption")
    ]
    app = _reopen(app, review_ids["B"])
    _assert_statuses(app, ("Failed", "Explicitly skipped", "Passed"))

    # Update B through the producer with the same saved review and AppTest session.
    publish_targeted(initial)
    assert a_handoff.read_bytes() == initial_a
    assert (initial / "B-scopeproof-manifest.json").read_bytes() == initial_b
    final_b = (initial / "B-targeted-scopeproof-manifest.json").read_bytes()
    assert b_handoff.read_bytes() == final_b
    app = _refresh_ci_status(app)
    _assert_statuses(app, ("Failed", "Failed", "Passed"))
    _assert_targeted_provenance(app, storage, review_ids["B"])

    # A same-repository manifest for A cannot substitute for the reviewed B commit.
    b_handoff.write_bytes(initial_a)
    app = _refresh_ci_status(app)
    _assert_statuses(app, ("Unknown", "Unknown", "Unknown"))
    assert not _panel(app).get("dataframe")
    assert "The local CI manifest could not be loaded for this exact review." in [
        error.value for error in _panel(app).get("error")
    ]

    b_handoff.unlink()
    app = _refresh_ci_status(app)
    _assert_statuses(app, ("Unknown", "Unknown", "Unknown"))
    assert not _panel(app).get("dataframe")
    assert "No local CI manifest was found for this exact review." in [
        caption.value for caption in _panel(app).get("caption")
    ]

    app = _reopen(app, review_ids["A"])
    _assert_statuses(app, ("Passed", "Passed", "Passed"))
    app = _reopen(app, review_ids["B"])
    b_handoff.write_bytes(final_b)
    app = _refresh_ci_status(app)
    _assert_statuses(app, ("Failed", "Failed", "Passed"))
    app = _upload(app, initial / "B-scopeproof-manifest.json")
    _assert_statuses(app, ("Failed", "Explicitly skipped", "Passed"))
    assert "CI source: manual upload." in [caption.value for caption in _panel(app).get("caption")]
    uploader, = _panel(app).get("file_uploader")
    app = uploader.set_value(None).run()
    assert not app.exception
    _assert_statuses(app, ("Failed", "Failed", "Passed"))
    assert {path: path.read_bytes() for path in storage.glob("*.json")} == saved_records
