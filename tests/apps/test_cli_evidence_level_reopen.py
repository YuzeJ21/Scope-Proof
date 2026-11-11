import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest

from scopeproof_core.cli import main
from scopeproof_core.schemas.models import EvidenceLevel
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.apps.test_streamlit_app import new_app, select_saved_review

PR_FIXTURE = (
    Path(__file__).resolve().parents[2] / "evals/fixtures/complete_implementation_pr.json"
)


def _save_cli_review(
    tmp_path: Path,
    storage: Path,
    recorded_level: EvidenceLevel,
) -> tuple[str, Path]:
    tmp_path.mkdir()
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\nInclude the CSV header\n", encoding="utf-8")
    criteria = tmp_path / "criteria.json"
    confirmation = tmp_path / "confirmation.json"

    assert main([
        "prepare-criteria", "--requirements", str(requirements), "--output", str(criteria),
    ]) == 0
    document = json.loads(criteria.read_text(encoding="utf-8"))
    document["criteria"][0]["required_evidence_level"] = recorded_level.value
    criteria.write_text(json.dumps(document), encoding="utf-8")

    source_inputs = ["--requirements", str(requirements), "--criteria", str(criteria)]
    assert main([
        "prepare-requirements-confirmation", *source_inputs,
        "--source-uri", "https://example.test/requirements", "--confirmed-by", "Fixture owner",
        "--output", str(confirmation),
    ]) == 0
    with redirect_stdout(StringIO()) as output:
        assert main([
            "review", *source_inputs, "--fixture", str(PR_FIXTURE),
            "--confirmation", str(confirmation), "--storage-dir", str(storage),
        ]) == 0
    saved_review = json.loads(output.getvalue())
    return saved_review["review_id"], Path(saved_review["record"])


@pytest.mark.parametrize(("recorded_level", "expected_options"), [
    pytest.param(EvidenceLevel.E0, ["E0", "E1", "E2", "E3"], id="E0"),
    pytest.param(EvidenceLevel.E4, ["E1", "E2", "E3", "E4"], id="E4"),
])
def test_workbench_reopens_confirmed_cli_evidence_level(
    recorded_level: EvidenceLevel,
    expected_options: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(storage))
    review_id, record = _save_cli_review(tmp_path / "typed", storage, recorded_level)
    ordinary_id, ordinary_record = _save_cli_review(
        tmp_path / "ordinary", storage, EvidenceLevel.E1,
    )
    original_bytes = record.read_bytes()
    ordinary_bytes = ordinary_record.read_bytes()
    original_state = JsonReviewStore(storage).load(review_id)
    assert original_state.criteria_revision.criteria[0].required_evidence_level is recorded_level

    app = select_saved_review(new_app(), review_id)
    app = app.button(key="reopen_review").click().run()

    assert not app.exception
    editor = app.selectbox(key="criterion_level_AC-01")
    assert editor.value == recorded_level
    assert editor.options == expected_options
    assert app.selectbox(key="criterion_level_AC-02").options == ["E1", "E2", "E3"]
    assert app.session_state["criteria_confirmed"] is True
    assert app.button(key="confirm_criteria").disabled
    assert app.session_state["review_state"] == original_state
    assert record.read_bytes() == original_bytes
    assert not app.download_button(key="download_json").disabled

    app = editor.set_value(EvidenceLevel.E2).run()

    assert not app.exception
    assert app.selectbox(key="criterion_level_AC-01").value == EvidenceLevel.E2
    assert not app.button(key="confirm_criteria").disabled
    assert app.button(key="run_analysis").disabled
    assert app.download_button(key="download_json").disabled
    assert app.session_state["criteria_confirmed"] is True
    assert app.session_state["review_state"] == original_state
    assert record.read_bytes() == original_bytes

    app = app.button(key="discard_criteria_draft").click().run()

    assert not app.exception
    assert app.selectbox(key="criterion_level_AC-01").value == recorded_level
    assert app.button(key="confirm_criteria").disabled
    assert not app.download_button(key="download_json").disabled
    assert app.session_state["review_state"] == original_state
    assert record.read_bytes() == original_bytes

    app = select_saved_review(app, ordinary_id)
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    assert app.selectbox(key="criterion_level_AC-01").value == EvidenceLevel.E1
    assert app.button(key="confirm_criteria").disabled
    assert app.session_state["review_state"].review.review_id == ordinary_id

    app = select_saved_review(app, review_id)
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    assert app.selectbox(key="criterion_level_AC-01").value == recorded_level
    assert app.button(key="confirm_criteria").disabled
    assert not app.download_button(key="download_json").disabled
    assert app.session_state["review_state"] == original_state
    assert record.read_bytes() == original_bytes
    assert ordinary_record.read_bytes() == ordinary_bytes


@pytest.mark.parametrize(("replacement", "expected_text"), [
    pytest.param("load_demo", "User can export the research list as CSV", id="demo"),
    pytest.param("prepare_criteria", "Archive an exported file", id="prepare"),
])
def test_replacing_reopened_cli_criteria_resets_the_editor(
    replacement: str,
    expected_text: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(storage))
    review_id, record = _save_cli_review(tmp_path / "typed", storage, EvidenceLevel.E4)
    original_bytes = record.read_bytes()
    app = select_saved_review(new_app(), review_id)
    app = app.button(key="reopen_review").click().run()
    assert app.selectbox(key="criterion_level_AC-01").value == EvidenceLevel.E4

    if replacement == "prepare_criteria":
        app = app.text_area(key="requirements_input").set_value(expected_text).run()
    assert not app.button(key=replacement).disabled
    app = app.button(key=replacement).click().run()

    assert not app.exception
    assert "AC-01 · Must Have · E1" in [item.label for item in app.expander]
    assert app.text_input(key="criterion_text_AC-01").value == expected_text
    editor = app.selectbox(key="criterion_level_AC-01")
    assert editor.value == EvidenceLevel.E1
    assert editor.options == ["E1", "E2", "E3"]
    assert any("Pending edits: None" in item.value for item in app.caption)
    assert app.session_state["criteria_confirmed"] is False
    assert app.button(key="run_analysis").disabled
    assert record.read_bytes() == original_bytes
