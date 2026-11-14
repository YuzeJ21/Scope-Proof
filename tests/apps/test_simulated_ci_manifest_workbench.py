"""Read the simulated pipeline's unedited CI artifacts in the actual workbench."""

import json
from pathlib import Path

from scripts.simulate_ci_manifest import simulate
from streamlit.testing.v1 import AppTest

from apps.web.launcher import WORKBENCH_STORAGE_ENV
from scopeproof_core.cli import main
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.apps.test_streamlit_app import APP_PATH, select_saved_review


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


def test_simulated_ci_manifests_open_for_both_builds(tmp_path, monkeypatch, capsys):
    output = tmp_path / "simulated-ci"
    simulate(output)
    capsys.readouterr()
    storage = tmp_path / "reviews"
    monkeypatch.setenv(WORKBENCH_STORAGE_ENV, str(storage))
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
    b_state = JsonReviewStore(storage).load(review_ids["B"])
    assert f"CI run B-targeted · {b_state.review.head_sha}" in [
        item.value for item in panel.get("text")
    ]
    assert app.session_state["review_state"] == b_state
    assert {path: path.read_bytes() for path in storage.glob("*.json")} == saved_records
