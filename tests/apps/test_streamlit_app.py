import json
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import pytest
from streamlit.testing.v1 import AppTest

from apps.web.view_models import (
    default_criterion_detail_id,
    prioritize_unresolved_criterion_ids,
)
from scopeproof_core.alpha.models import AlphaOutcome
from scopeproof_core.alpha.storage import (
    JsonAlphaCaseStore,
    default_alpha_case_directory,
)
from scopeproof_core.demo import load_demo_snapshot
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.github.client import GitHubNetworkError, GitHubPaginationError
from scopeproof_core.importers.junit import (
    JUnitMappingSelection,
    build_junit_evidence_import,
)
from scopeproof_core.reviews.lifecycle import (
    append_external_verification,
    append_junit_evidence_import,
    append_resolution,
)
from scopeproof_core.schemas.models import (
    CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
    JUNIT_EVIDENCE_BOUNDARY_DESCRIPTION,
    RULESET_VERSION,
    CheckState,
    CIObservation,
    EvidenceLevel,
    EvidenceSourceScope,
    GateVerdict,
    HumanDecision,
    IngestionState,
    Priority,
    RepositoryVisibility,
    ResearchContext,
    ResolutionEvent,
    ReviewState,
    RuntimeEvidence,
)
from scopeproof_core.storage.json_store import (
    JsonReviewStore,
    default_local_review_directory,
)
from scopeproof_core.verification.service import build_findings

APP_PATH = Path(__file__).resolve().parents[2] / "apps" / "web" / "app.py"


def new_app() -> AppTest:
    return AppTest.from_file(str(APP_PATH)).run()


def load_demo(app: AppTest) -> AppTest:
    app = app.button(key="load_demo").click().run()
    return app.text_input(key="criteria_source_confirmer").set_value(
        "Local reviewer"
    ).run()


def analyzed_demo(app: AppTest) -> AppTest:
    app = load_demo(app)
    app = app.button(key="confirm_criteria").click().run()
    return app.button(key="run_analysis").click().run()


def analyzed_standard_demo(app: AppTest) -> AppTest:
    app = app.button(key="load_demo").click().run()
    app.session_state["snapshot"] = app.session_state["snapshot"].model_copy(
        update={"repository_visibility": RepositoryVisibility.VERIFIED_PUBLIC}
    )
    app.session_state["criteria_source_mode"] = "standard"
    app = app.run()
    app = app.text_input(key="criteria_source_reference").set_value(
        "https://github.com/acme/repo/issues/6"
    ).run()
    app = app.text_input(key="criteria_source_confirmer").set_value(
        "Product owner"
    ).run()
    app = app.button(key="confirm_criteria").click().run()
    return app.button(key="run_analysis").click().run()


def analyzed_exact_head_standard_demo(app: AppTest) -> AppTest:
    app = app.button(key="load_demo").click().run()
    app.session_state["snapshot"] = app.session_state["snapshot"].model_copy(
        update={
            "head_sha": "a" * 40,
            "repository_visibility": RepositoryVisibility.VERIFIED_PUBLIC,
        }
    )
    app.session_state["criteria_source_mode"] = "standard"
    app = app.run()
    app = app.text_input(key="criteria_source_reference").set_value(
        "https://github.com/acme/repo/issues/6"
    ).run()
    app = app.text_input(key="criteria_source_confirmer").set_value(
        "Product owner"
    ).run()
    app = app.button(key="confirm_criteria").click().run()
    return app.button(key="run_analysis").click().run()


def resolve_all_criteria(app: AppTest) -> AppTest:
    state = app.session_state["review_state"]
    resolved_criterion_ids = {
        resolution.criterion_id
        for resolution in (state.bundle.resolutions if state.bundle is not None else [])
    }
    for criterion in state.criteria_revision.criteria:
        if criterion.criterion_id in resolved_criterion_ids:
            continue
        state = append_resolution(
            state,
            ResolutionEvent(
                criterion_id=criterion.criterion_id,
                decision=HumanDecision.ACCEPTED,
                comment="Reviewed candidate evidence",
            ),
        )
    app.session_state["review_state"] = state
    app.session_state["bundle"] = state.bundle
    return app.run()


def saved_demo_review(app: AppTest) -> tuple[AppTest, str]:
    app = analyzed_demo(app)
    review_id = app.session_state["review_state"].review.review_id
    return app, review_id


def _assert_pending_draft_preserves_authoritative_review(
    app: AppTest,
    *,
    review_id: str,
    authoritative_state: ReviewState,
) -> None:
    download_keys = [button.key for button in app.download_button]

    assert app.session_state["review_state"] == authoritative_state
    assert JsonReviewStore(default_local_review_directory()).load(
        review_id
    ) == authoritative_state
    assert download_keys == [
        "download_markdown",
        "download_json",
        "download_csv",
    ]
    assert all(app.download_button(key=key).disabled for key in download_keys)


def _review_fingerprint_for_test(state: ReviewState) -> str:
    return sha256(state.model_dump_json().encode("utf-8")).hexdigest()


def select_saved_review(app: AppTest, review_id: str) -> AppTest:
    return app.selectbox(key="saved_reopen_review_id").set_value(review_id).run()


def evidence_matrix_criterion_ids(app: AppTest) -> list[str]:
    prefix = "**Criterion:** "
    return [
        item.value.removeprefix(prefix)
        for item in app.markdown
        if item.value.startswith(prefix)
    ]


def _main_widget_keys(app: object) -> list[str]:
    keys: list[str] = []

    def collect(node: object) -> None:
        key = getattr(node, "key", None)
        if isinstance(key, str):
            keys.append(key)
        children = getattr(node, "children", {})
        for child in children.values():
            collect(child)

    collect(getattr(app, "main", app))
    return keys


def qualified_alpha_analyzed_app(app: AppTest) -> AppTest:
    app = app.checkbox(key="alpha_feedback_mode").check().run()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/repo/pull/7"
    ).run()
    app = app.text_input(key="requirements_source_url").set_value(
        "https://github.com/acme/repo/issues/6"
    ).run()
    app = app.checkbox(key="source_owner_confirmed").check().run()
    app = app.checkbox(key="no_confidential_information").check().run()
    snapshot = load_demo_snapshot().model_copy(
        update={
            "repository": "acme/repo",
            "repository_visibility": RepositoryVisibility.VERIFIED_PUBLIC,
            "pr_number": 7,
            "head_sha": "a" * 40,
        }
    )
    with patch(
        "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
        return_value=snapshot,
    ):
        app = app.button(key="fetch_pr").click().run()
    app = app.text_area(key="requirements_input").set_value("Export CSV").run()
    app = app.button(key="prepare_criteria").click().run()
    app = app.text_input(key="criteria_source_confirmer").set_value(
        "Alpha source owner"
    ).run()
    app = app.button(key="confirm_criteria").click().run()
    return app.button(key="run_analysis").click().run()


def test_summary_places_exports_before_local_storage() -> None:
    app = analyzed_demo(new_app())
    keys = _main_widget_keys(app)

    assert keys.index("download_markdown") < keys.index("save_review")
    assert keys.index("download_json") < keys.index("save_review")
    assert keys.index("download_csv") < keys.index("save_review")


def test_storage_path_is_kept_inside_local_storage_details() -> None:
    app = analyzed_demo(new_app())
    local_storage = next(
        item for item in app.expander if item.label == "Local review storage"
    )

    assert any(
        caption.value.startswith("Storage directory:")
        for caption in local_storage.caption
    )


def test_optional_source_revision_is_collapsed_by_default() -> None:
    app = load_demo(new_app())
    revision = next(
        item for item in app.expander if item.label == "Source revision (optional)"
    )

    assert revision.proto.expanded is False
    assert revision.text_input(key="criteria_source_revision")


def test_constructed_demo_disclosure_is_not_shown_for_standard_review() -> None:
    demo = analyzed_demo(new_app())
    standard = analyzed_standard_demo(new_app())
    disclosure = (
        "The bundled CSV export case is a deliberately constructed demo, "
        "not a real production incident."
    )

    assert disclosure in [item.value for item in demo.caption]
    assert disclosure not in [item.value for item in standard.caption]


def test_standard_analysis_rejects_unverified_repository_snapshot() -> None:
    app = load_demo(new_app())
    app.session_state["criteria_source_mode"] = "standard"
    app = app.run()
    app = app.text_input(key="criteria_source_reference").set_value(
        "https://github.com/acme/repo/issues/6"
    ).run()
    app = app.text_input(key="criteria_source_confirmer").set_value(
        "Product owner"
    ).run()
    app = app.button(key="confirm_criteria").click().run()

    app = app.button(key="run_analysis").click().run()

    assert app.session_state["review_state"] is None
    assert any("could not be completed" in item.value for item in app.error)


def test_alpha_outcome_is_ready_after_authoritative_review_autosaves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = qualified_alpha_analyzed_app(new_app())
    app = app.selectbox(key="alpha_outcome").set_value(
        AlphaOutcome.FOUND_USEFUL_GAP
    ).run()

    assert app.button(key="record_alpha_outcome").disabled is False
    assert _main_widget_keys(app).index("download_csv") < _main_widget_keys(app).index(
        "record_alpha_outcome"
    )


def test_analysis_is_disabled_before_criteria_confirmation() -> None:
    app = new_app()
    assert app.button(key="run_analysis").disabled is True


def test_standard_review_requires_source_reference_and_confirmer_before_confirmation() -> None:
    app = new_app()
    app = app.text_area(key="requirements_input").set_value(
        "The result can be exported as CSV."
    ).run()
    app = app.button(key="prepare_criteria").click().run()

    assert app.button(key="confirm_criteria").disabled is True
    app = app.text_input(key="criteria_source_reference").set_value(
        "https://github.com/acme/repo/issues/6"
    ).run()
    assert app.button(key="confirm_criteria").disabled is True

    app = app.text_input(key="criteria_source_confirmer").set_value(
        "Product owner"
    ).run()
    assert app.button(key="confirm_criteria").disabled is False


def test_demo_preloads_read_only_source_but_requires_human_confirmer() -> None:
    app = new_app().button(key="load_demo").click().run()

    source_reference = app.text_input(key="criteria_source_reference")
    assert source_reference.value == CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI
    assert source_reference.disabled is True
    assert app.button(key="confirm_criteria").disabled is True

    app = app.text_input(key="criteria_source_confirmer").set_value(
        "Demo reviewer"
    ).run()
    assert app.button(key="confirm_criteria").disabled is False


def test_alpha_confirmation_reuses_public_requirements_source_without_duplicate_input() -> None:
    app = new_app().checkbox(key="alpha_feedback_mode").check().run()
    source_url = "https://github.com/acme/repo/issues/6"
    app = app.text_input(key="requirements_source_url").set_value(source_url).run()
    app = app.text_area(key="requirements_input").set_value(
        "The result can be exported as CSV."
    ).run()
    app = app.button(key="prepare_criteria").click().run()

    assert not [
        item for item in app.text_input if item.key == "criteria_source_reference"
    ]
    assert source_url in [item.value for item in app.code]
    assert app.button(key="confirm_criteria").disabled is True

    app = app.text_input(key="criteria_source_confirmer").set_value(
        "Source owner"
    ).run()
    assert app.button(key="confirm_criteria").disabled is False


def test_confirmation_persists_exact_source_snapshot_with_utc_time() -> None:
    app = load_demo(new_app())
    app = app.text_input(key="criteria_source_revision").set_value(
        "demo-fixture@2026-08-02"
    ).run()
    app = app.button(key="confirm_criteria").click().run()

    provenance = app.session_state["criteria_source_provenance"]
    assert provenance.source_uri == CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI
    assert provenance.source_revision == "demo-fixture@2026-08-02"
    assert provenance.confirmed_by == "Local reviewer"
    assert provenance.source_text_sha256 == sha256(
        app.session_state["source_text"].encode("utf-8")
    ).hexdigest()
    assert len(provenance.normalized_criteria_sha256) == 64
    assert provenance.confirmed_at.tzinfo is UTC


def test_confirmation_writes_normalized_source_uri_back_to_the_active_widget() -> None:
    app = new_app().button(key="load_demo").click().run()
    app.session_state["criteria_source_mode"] = "standard"
    app = app.run()
    app = app.text_input(key="criteria_source_reference").set_value(
        "https://EXAMPLE.com:443/requirements"
    ).run()
    app = app.text_input(key="criteria_source_confirmer").set_value(
        "Product owner"
    ).run()

    app = app.button(key="confirm_criteria").click().run()

    assert not app.exception
    assert app.session_state["criteria_source_provenance"].source_uri == (
        "https://example.com/requirements"
    )
    assert app.text_input(key="criteria_source_reference").value == (
        "https://example.com/requirements"
    )
    assert app.button(key="run_analysis").disabled is False
    assert not any(
        item.value.startswith("Criteria source changes are pending confirmation.")
        for item in app.warning
    )


def test_source_revision_change_is_pending_and_reconfirmation_appends_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = analyzed_demo(new_app())
    authoritative_state = app.session_state["review_state"].model_copy(deep=True)

    app = app.text_input(key="criteria_source_revision").set_value(
        "demo-fixture@second"
    ).run()

    assert app.session_state["review_state"] == authoritative_state
    assert app.button(key="confirm_criteria").disabled is False
    assert app.button(key="save_review").disabled is True
    assert all(button.disabled for button in app.download_button)
    assert any(
        item.value.startswith("Criteria source changes are pending confirmation.")
        for item in app.warning
    )
    assert "Complete — Criteria confirmed" not in "\n".join(
        item.value for item in app.sidebar.markdown
    )

    app = app.button(key="confirm_criteria").click().run()
    revised = app.session_state["review_state"]
    assert revised.criteria_revision.number == 2
    assert revised.bundle is None
    assert revised.review.criteria_source_provenance.source_revision == (
        "demo-fixture@second"
    )
    assert app.button(key="run_analysis").disabled is False


def test_pending_source_draft_survives_an_early_delete_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    pending_revision = "demo-fixture@pending"
    app = app.text_input(key="criteria_source_revision").set_value(
        pending_revision
    ).run()
    app = select_saved_review(app, review_id)
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()

    app = app.button(key="delete_saved_review").click().run()

    assert app.text_input(key="criteria_source_revision").value == pending_revision
    assert app.button(key="confirm_criteria").disabled is False
    assert any(
        item.value.startswith("Criteria source changes are pending confirmation.")
        for item in app.warning
    )


def test_second_provenance_only_reconfirmation_revises_bundleless_state() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="criteria_source_revision").set_value(
        "demo-fixture@second"
    ).run()
    app = app.button(key="confirm_criteria").click().run()
    first_reconfirmation = app.session_state["review_state"]
    assert first_reconfirmation.criteria_revision.number == 2
    assert first_reconfirmation.bundle is None

    app = app.run()
    app = app.text_input(key="criteria_source_confirmer").set_value(
        "Second reviewer"
    ).run()
    app = app.button(key="confirm_criteria").click().run()

    second_reconfirmation = app.session_state["review_state"]
    assert second_reconfirmation.criteria_revision.number == 3
    assert second_reconfirmation.review.criteria_source_provenance.confirmed_by == (
        "Second reviewer"
    )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("criteria_source_reference", "https://github.com/acme/repo/issues/8"),
        ("criteria_source_revision", "requirements@second"),
        ("criteria_source_confirmer", "QA owner"),
    ],
)
def test_each_source_identity_change_blocks_authoritative_actions(
    key: str,
    value: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = analyzed_standard_demo(new_app())
    authoritative_state = app.session_state["review_state"].model_copy(deep=True)

    app = app.text_input(key=key).set_value(value).run()

    assert app.session_state["review_state"] == authoritative_state
    assert app.button(key="confirm_criteria").disabled is False
    assert app.button(key="save_review").disabled is True
    assert app.button(key="record_final_acceptance").disabled is True
    assert all(button.disabled for button in app.download_button)


def test_invalid_source_reference_does_not_mutate_unconfirmed_review() -> None:
    app = new_app().button(key="load_demo").click().run()
    app.session_state["criteria_source_mode"] = "standard"
    app = app.run()
    original_criteria = list(app.session_state["criteria"])
    app = app.text_input(key="criteria_source_reference").set_value(
        "http://github.com/acme/repo/issues/6"
    ).run()
    app = app.text_input(key="criteria_source_confirmer").set_value(
        "Product owner"
    ).run()

    app = app.button(key="confirm_criteria").click().run()

    assert not app.exception
    assert app.session_state["criteria"] == original_criteria
    assert app.session_state["criteria_confirmed"] is False
    assert app.session_state["review_state"] is None
    assert app.session_state["criteria_source_provenance"] is None
    assert any("Criteria could not be confirmed." in item.value for item in app.error)


def test_confirmed_source_is_visible_in_one_collapsed_details_panel() -> None:
    app = analyzed_demo(new_app())

    details = next(
        item for item in app.expander if item.label == "Confirmed criteria source"
    )
    assert details.proto.expanded is False
    visible = "\n".join(
        item.value for item in [*details.caption, *details.code, *details.text]
    )
    assert CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI in visible
    assert "Local reviewer" in visible
    assert app.session_state[
        "criteria_source_provenance"
    ].source_text_sha256 in visible


def test_legacy_review_without_source_provenance_is_safe_and_fail_closed() -> None:
    app = analyzed_demo(new_app())
    legacy = app.session_state["review_state"].model_copy(deep=True)
    legacy.review = legacy.review.model_copy(
        update={"criteria_source_provenance": None}
    )
    legacy.criteria_revision = legacy.criteria_revision.model_copy(
        update={"source_provenance": None}
    )
    assert legacy.bundle is not None
    legacy.bundle.review = legacy.bundle.review.model_copy(
        update={"criteria_source_provenance": None}
    )
    app.session_state["review_state"] = legacy
    app.session_state["bundle"] = legacy.bundle
    app.session_state["criteria_source_provenance"] = None
    app.session_state["criteria_source_mode"] = "standard"
    app.session_state["criteria_source_reference"] = ""
    app.session_state["criteria_source_revision"] = ""
    app.session_state["criteria_source_confirmer"] = ""

    app = app.run()

    assert not app.exception
    assert any(
        "legacy review has no criteria source provenance" in item.value
        for item in app.warning
    )
    assert "Criteria confirmed by the reviewer." not in [
        item.value for item in app.success
    ]
    assert all(button.disabled for button in app.download_button)
    assert app.button(key="record_final_acceptance").disabled is True


def test_workbench_heading_order_uses_one_h1_and_numbered_h2_sections() -> None:
    app = analyzed_demo(new_app())

    assert [item.value for item in app.title] == ["ScopeProof"]
    assert [item.value for item in app.header] == [
        "1 · Start Review",
        "2 · Confirm Criteria",
        "3 · Decision Progress",
        "4 · Criterion Review",
        "5 · Evidence Matrix",
        "6 · Summary & Export",
    ]
    assert not app.subheader
    assert not app.sidebar.header


def test_readme_workbench_steps_match_rendered_numbered_sections() -> None:
    app = analyzed_demo(new_app())
    readme_lines = (APP_PATH.parents[2] / "README.md").read_text(
        encoding="utf-8"
    ).splitlines()
    list_heading_index = next(
        index
        for index, line in enumerate(readme_lines)
        if line.startswith("The ") and " review " in line and line.endswith(" are:")
    )
    documented_sections: list[str] = []
    for line in readme_lines[list_heading_index + 1 :]:
        if line and line[0].isdigit() and ". " in line:
            documented_sections.append(line.split(". ", maxsplit=1)[1].removesuffix("."))
        elif documented_sections:
            break

    assert documented_sections == [
        item.value.split(" · ", maxsplit=1)[1] for item in app.header
    ]


def test_product_disclaimer_is_visible() -> None:
    app = new_app()
    markdown_text = [markdown.value for markdown in app.markdown]
    caption_text = [caption.value for caption in app.caption]
    visible_text = "\n".join(
        [*markdown_text, *caption_text]
    )
    assert "does not replace QA" in visible_text
    assert "No paid LLM API" in visible_text


def test_workbench_defines_visible_keyboard_focus_treatment() -> None:
    source = APP_PATH.read_text(encoding="utf-8")

    assert ":focus-visible" in source
    assert "outline: 3px solid #ffbf47" in source


def test_standard_review_hides_alpha_research_fields() -> None:
    app = new_app()

    assert app.checkbox(key="alpha_feedback_mode").value is False
    assert not [item for item in app.text_input if item.key == "requirements_source_url"]


def test_alpha_mode_creates_case_after_confirming_criteria(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = qualified_alpha_analyzed_app(new_app())

    assert app.session_state["alpha_case_id"].startswith("alpha-")
    assert app.button(key="record_alpha_outcome").disabled is True
    app = app.selectbox(key="alpha_outcome").set_value(
        AlphaOutcome.FOUND_USEFUL_GAP
    ).run()
    assert app.button(key="record_alpha_outcome").disabled is False
    app = app.button(key="record_alpha_outcome").click().run()
    assert not app.error, [item.value for item in app.error]

    record = JsonAlphaCaseStore(default_alpha_case_directory()).load(
        app.session_state["alpha_case_id"]
    )
    assert record.repository_visibility is RepositoryVisibility.VERIFIED_PUBLIC
    assert record.outcome is AlphaOutcome.FOUND_USEFUL_GAP
    assert record.publication_consent.report is False
    assert record.publication_consent.quote is False


def test_alpha_mode_does_not_qualify_an_unverified_loaded_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = new_app().checkbox(key="alpha_feedback_mode").check().run()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/repo/pull/7"
    ).run()
    app = app.text_input(key="requirements_source_url").set_value(
        "https://github.com/acme/repo/issues/6"
    ).run()
    app = app.checkbox(key="source_owner_confirmed").check().run()
    app = app.checkbox(key="no_confidential_information").check().run()
    snapshot = load_demo_snapshot().model_copy(
        update={"repository": "acme/repo", "pr_number": 7, "head_sha": "a" * 40}
    )
    with patch(
        "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
        return_value=snapshot,
    ):
        app = app.button(key="fetch_pr").click().run()
    app = app.text_area(key="requirements_input").set_value("Export CSV").run()
    app = app.button(key="prepare_criteria").click().run()
    app = app.text_input(key="criteria_source_confirmer").set_value(
        "Alpha source owner"
    ).run()

    app = app.button(key="confirm_criteria").click().run()

    assert app.session_state["alpha_case_id"] is None
    assert any("could not be confirmed" in item.value for item in app.error)


@pytest.mark.parametrize(
    ("widget_kind", "widget_key", "value"),
    [
        ("text_input", "criteria_source_confirmer", "Second source owner"),
        ("text_input", "criteria_source_revision", "requirements@second"),
        (
            "text_input",
            "requirements_source_url",
            "https://github.com/acme/repo/issues/8",
        ),
        ("text_input", "criterion_text_AC-01", "Export the filtered rows as CSV"),
    ],
)
def test_reconfirmed_alpha_inputs_create_new_case_and_preserve_original(
    widget_kind: str,
    widget_key: str,
    value: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = qualified_alpha_analyzed_app(new_app())
    store = JsonAlphaCaseStore(default_alpha_case_directory())
    original_case_id = app.session_state["alpha_case_id"]
    original_record = store.load(original_case_id)

    widget = getattr(app, widget_kind)(key=widget_key)
    app = widget.set_value(value).run()
    app = app.button(key="confirm_criteria").click().run()

    revised_case_id = app.session_state["alpha_case_id"]
    assert not app.exception
    assert not app.error
    assert revised_case_id != original_case_id
    assert store.load(original_case_id) == original_record
    revised_record = store.load(revised_case_id)
    assert revised_record.criteria_source_provenance == (
        app.session_state["criteria_source_provenance"]
    )
    assert revised_record.confirmed_criteria == [
        criterion.text for criterion in app.session_state["criteria"]
    ]


def test_primary_workbench_uses_acceptance_coverage_language() -> None:
    app = analyzed_demo(new_app())
    visible_text = "\n".join(
        [
            *(item.value for item in app.markdown),
            *(item.value for item in app.subheader),
            *(item.value for item in app.caption),
        ]
    )

    assert "See which acceptance criteria have credible PR evidence" in visible_text
    matrix_captions = [item.value for item in app.caption]
    assert "Requirement" in matrix_captions
    assert "Priority: Must have" in matrix_captions
    assert "Evidence status: Strong candidate" in matrix_captions
    assert "Evidence types: Implementation, Test" in matrix_captions
    assert "Reviewer decision: Unresolved" in matrix_captions
    assert "Prove the PR matches the product intent" not in visible_text


def test_loaded_source_identity_does_not_repeat_ci_diagnostics() -> None:
    app = load_demo(new_app())

    captions = "\n".join(item.value for item in app.caption)

    assert "Loaded source" in "\n".join(item.value for item in app.markdown)
    assert "head-demo-002" in [item.value for item in app.code]
    assert "Observed CI state:" not in captions
    assert "Observed CI reason:" not in captions


def test_loaded_source_identity_renders_repository_as_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    repository = "![untrusted repository](https://example.invalid/repository.png)"
    snapshot = load_demo_snapshot().model_copy(update={"repository": repository})

    with patch("scopeproof_core.demo.load_demo_snapshot", return_value=snapshot):
        app = load_demo(new_app())

    assert repository not in "\n".join(item.value for item in app.markdown)
    assert f"{repository} · PR #{snapshot.pr_number}" in [item.value for item in app.text]


def test_evidence_matrix_ci_summary_is_compact_complete_and_deterministic() -> None:
    app = analyzed_demo(new_app())
    details = next(
        item for item in app.expander if item.label == "CI details and evidence boundary"
    )
    visible = "\n".join(item.value for item in [*app.caption, *app.text, *app.warning])

    assert details.proto.expanded is False
    assert "Observed CI: Passing" in visible
    assert "Collection: Complete" in visible
    assert "1 total · 1 successful · 0 pending · 0 failing" in visible
    assert "0 neutral · 0 skipped · 0 concrete legacy statuses" in visible
    assert "Runtime verification: Not recorded" in visible
    assert app.session_state["review_state"].review.ci_observation.reason in visible


def test_limiting_ci_warning_is_visible_outside_collapsed_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    snapshot = load_demo_snapshot().model_copy(
        update={
            "ci_observation": CIObservation(
                state="unavailable",
                reason="Observed 1 skipped check run; it does not prove passing.",
                total_check_runs=1,
                skipped_check_runs=1,
                skipped_check_names=["integration"],
                collection_complete=False,
                collection_notes=["Check-run collection was incomplete."],
            ),
            "check_state": CheckState.UNAVAILABLE,
        }
    )
    with patch("scopeproof_core.demo.load_demo_snapshot", return_value=snapshot):
        app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    details = next(
        item for item in app.expander if item.label == "CI details and evidence boundary"
    )
    visible = "\n".join(item.value for item in [*app.caption, *app.warning])
    details_text = "\n".join(item.value for item in details.text)

    assert details.proto.expanded is False
    assert (
        "Observed CI has a limiting state. Review its deterministic reason before relying on "
        "the gate."
    ) in "\n".join(item.value for item in app.warning)
    assert "integration" not in visible
    assert "Check-run collection was incomplete." not in visible
    assert "integration" in details_text
    assert "Check-run collection was incomplete." in details_text


def test_complete_passing_ci_with_skipped_check_warns_without_changing_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    snapshot = load_demo_snapshot().model_copy(
        update={
            "ci_observation": CIObservation(
                state=CheckState.PASSING,
                reason="One successful check and one skipped check were observed.",
                total_check_runs=2,
                successful_check_runs=1,
                skipped_check_runs=1,
                skipped_check_names=["integration"],
                collection_complete=True,
            ),
            "check_state": CheckState.PASSING,
        }
    )
    with patch("scopeproof_core.demo.load_demo_snapshot", return_value=snapshot):
        app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    review_state = app.session_state["review_state"]
    details = next(
        item for item in app.expander if item.label == "CI details and evidence boundary"
    )
    visible_warning = (
        "Observed CI includes skipped checks. Skipped checks were not executed; review its "
        "deterministic reason and CI details before relying on the gate."
    )

    assert review_state.review.check_state is CheckState.PASSING
    assert review_state.review.ci_observation.state is CheckState.PASSING
    assert visible_warning in [item.value for item in app.warning]
    assert "integration" not in "\n".join(item.value for item in app.warning)
    assert "integration" in [item.value for item in details.text]


def test_active_and_reopened_research_review_show_evidence_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = analyzed_demo(new_app())
    state = app.session_state["review_state"]
    assert state.bundle is not None
    unsafe_skipped_check = "![skipped](https://example.invalid/skipped.png)"
    unsafe_boundary_note = "![boundary](https://example.invalid/boundary.png)"
    unsafe_collection_note = "![diagnostic](https://example.invalid/diagnostic.png)"
    review = state.review.model_copy(
        update={
            "check_state": CheckState.UNAVAILABLE,
            "ci_observation": CIObservation(
                reason="Only skipped CI was observed.",
                total_check_runs=1,
                skipped_check_runs=1,
                skipped_check_names=[unsafe_skipped_check],
                collection_complete=False,
                collection_notes=[unsafe_collection_note],
            ),
        }
    )
    research_bundle = state.bundle.model_copy(
        update={
            "review": review,
            "research_context": ResearchContext(
                case_id="R-001",
                boundary_note=unsafe_boundary_note,
            )
        }
    )
    research_state = state.model_copy(update={"review": review, "bundle": research_bundle})
    JsonReviewStore(default_local_review_directory()).save(research_state)
    app.session_state["review_state"] = research_state
    app.session_state["bundle"] = research_bundle
    app = app.run()

    active_text = "\n".join(
        [*(item.value for item in app.markdown), *(item.value for item in app.caption)]
    )
    assert "Public engineering research" in active_text
    assert "Stage 1 credit: 0" in active_text
    assert "Deterministic reason" in active_text
    assert "Static candidates and observed CI do not establish runtime verification." in active_text
    assert "Runtime verification: Not recorded" in active_text
    assert unsafe_skipped_check not in active_text
    assert unsafe_boundary_note not in active_text
    assert unsafe_collection_note not in active_text
    assert unsafe_skipped_check in [item.value for item in app.text]
    assert unsafe_boundary_note in [item.value for item in app.text]
    assert unsafe_collection_note in [item.value for item in app.text]

    reopened = new_app()
    reopened = select_saved_review(reopened, research_state.review.review_id)
    reopened = reopened.button(key="reopen_review").click().run()
    reopened_text = "\n".join(
        [*(item.value for item in reopened.markdown), *(item.value for item in reopened.caption)]
    )
    assert "Public engineering research" in reopened_text
    assert "Stage 1 credit: 0" in reopened_text
    assert "Deterministic reason" in reopened_text
    assert "Runtime verification: Not recorded" in reopened_text
    assert unsafe_skipped_check not in reopened_text
    assert unsafe_boundary_note not in reopened_text
    assert unsafe_collection_note not in reopened_text
    assert unsafe_skipped_check in [item.value for item in reopened.text]
    assert unsafe_boundary_note in [item.value for item in reopened.text]
    assert unsafe_collection_note in [item.value for item in reopened.text]


def test_active_and_reopened_review_show_recorded_runtime_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = analyzed_demo(new_app())
    state = app.session_state["review_state"]
    assert state.bundle is not None
    recorded_bundle = state.bundle.model_copy(
        update={
            "runtime_evidence": [
                RuntimeEvidence(
                    criterion_id="AC-01",
                    artifact_reference="https://example.test/runs/1",
                    scenario="Controlled runtime scenario",
                    environment="test",
                    result="passed",
                    reviewer="QA",
                    evidence_level=EvidenceLevel.E3,
                )
            ]
        }
    )
    recorded_state = state.model_copy(update={"bundle": recorded_bundle})
    JsonReviewStore(default_local_review_directory()).save(recorded_state)
    app.session_state["review_state"] = recorded_state
    app.session_state["bundle"] = recorded_bundle
    app = app.run()
    assert "Runtime verification: Recorded" in [item.value for item in app.caption]

    reopened = new_app()
    reopened = select_saved_review(reopened, recorded_state.review.review_id)
    reopened = reopened.button(key="reopen_review").click().run()
    assert "Runtime verification: Recorded" in [item.value for item in reopened.caption]


def test_criterion_detail_shows_bounded_candidate_context() -> None:
    app = analyzed_demo(new_app())

    assert "Bounded context" in [item.value for item in app.caption]
    assert any(
        "export_research_list_csv" in item.value and "filtered_rows" in item.value
        for item in app.code
    )


def test_partial_public_pr_fetch_shows_bounded_analysis_and_skipped_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    snapshot = load_demo_snapshot().model_copy(
        update={
            "ingestion_state": IngestionState.PARTIAL,
            "warnings": [
                "File limit reached; skipped 2 changed files.",
                "![remote image](https://example.invalid/pixel.png)",
            ],
            "skipped_files": ["src/one.py", "src/two.py"],
        }
    )
    app = new_app()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/repo/pull/7"
    ).run()
    with patch(
        "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
        return_value=snapshot,
    ):
        app = app.button(key="fetch_pr").click().run()

    warning_text = "\n".join(item.value for item in app.warning)
    assert "Partial PR ingestion" in warning_text
    assert "gate cannot be Ready" in warning_text
    assert "File limit reached; skipped 2 changed files." not in warning_text
    code_text = "\n".join(item.value for item in app.code)
    assert "File limit reached; skipped 2 changed files." in code_text
    assert "![remote image](https://example.invalid/pixel.png)" in code_text
    assert [item.label for item in app.expander if "Skipped changed files" in item.label] == [
        "Skipped changed files (2)"
    ]
    assert "src/one.py" in code_text


def test_reopened_partial_review_keeps_ingestion_recovery_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    snapshot = load_demo_snapshot().model_copy(
        update={
            "ingestion_state": IngestionState.PARTIAL,
            "warnings": ["File limit reached; skipped 1 changed files."],
            "skipped_files": ["src/reopen-skipped.py"],
        }
    )
    app = new_app()
    with patch("scopeproof_core.demo.load_demo_snapshot", return_value=snapshot):
        app = app.button(key="load_demo").click().run()
    app = app.text_input(key="criteria_source_confirmer").set_value(
        "Local reviewer"
    ).run()
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    review_id = app.session_state["review_state"].review.review_id

    fresh = select_saved_review(new_app(), review_id)
    fresh = fresh.button(key="reopen_review").click().run()

    warning_text = "\n".join(item.value for item in fresh.warning)
    assert "Partial PR ingestion" in warning_text
    code_text = "\n".join(item.value for item in fresh.code)
    assert "File limit reached; skipped 1 changed files." in code_text
    assert "src/reopen-skipped.py" in code_text


def test_public_pr_entry_precedes_optional_start_review_controls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = new_app()
    keys = _main_widget_keys(app)

    assert keys.count("pr_url") == 1
    assert keys.count("fetch_pr") == 1
    assert keys.index("pr_url") < keys.index("fetch_pr")
    assert keys.index("fetch_pr") < keys.index("load_demo")
    assert keys.index("fetch_pr") < keys.index("alpha_feedback_mode")
    assert keys.index("fetch_pr") < keys.index("github_token")
    assert keys.index("fetch_pr") < keys.index("candidate_paths")
    assert keys.index("fetch_pr") < keys.index("reopen_review_id")
    assert keys.index("fetch_pr") < keys.index("requirements_input")


def test_start_review_secondary_paths_are_collapsed_after_public_pr_entry() -> None:
    app = new_app()

    assert [item.label for item in app.expander[:3]] == [
        "Advanced source options",
        "Research and historical options",
        "Resume a saved review",
    ]
    assert all(item.proto.expanded is False for item in app.expander[:3])
    assert app.button(key="load_demo").label == "Load deliberately constructed demo"
    assert app.button(key="reopen_review").disabled is True


def test_owner_led_first_use_keeps_demo_visible_and_research_feedback_secondary() -> None:
    app = new_app()
    keys = _main_widget_keys(app)
    visible = "\n".join(item.value for item in [*app.markdown, *app.caption])

    assert "Deliberately constructed demonstration" in visible
    assert "constructed-demo-tagged" in visible
    assert "segregated from genuine review claims" in visible
    assert keys.index("candidate_paths") < keys.index("alpha_feedback_mode")
    assert "Stage 1 is closed" in visible
    assert "not required for owner-led Stage 2" in visible


def test_criteria_confirmation_explains_draft_submission_boundary() -> None:
    app = load_demo(new_app())
    caption_text = "\n".join(item.value for item in app.caption)

    assert "Typing or pressing Enter only stages draft changes" in caption_text
    assert app.button(key="confirm_criteria").label == "Apply edits and confirm criteria"


def test_saved_review_is_discoverable_and_selectable_in_a_fresh_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_state = saved.session_state["review_state"]

    fresh = new_app()
    saved_ids = fresh.selectbox(key="saved_reopen_review_id")
    assert saved_ids.options == [review_id]
    assert saved_ids.value is None
    assert fresh.button(key="reopen_review").disabled is True
    caption_text = "\n".join(item.value for item in fresh.caption)
    assert "1 saved local review found" in caption_text
    assert "validated when opened" in caption_text

    fresh = saved_ids.set_value(review_id).run()
    fresh = fresh.button(key="reopen_review").click().run()

    assert fresh.session_state["review_state"] == saved_state
    assert "Review reopened from local storage" in "\n".join(
        message.value for message in fresh.success
    )


def test_authoritative_review_autosaves_without_manual_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    app = analyzed_demo(new_app())
    state = app.session_state["review_state"]
    stored = JsonReviewStore(default_local_review_directory()).load(
        state.review.review_id
    )

    assert stored == state
    assert app.session_state["saved_review_fingerprint"] is not None
    assert app.session_state["failed_review_save_fingerprint"] is None
    assert app.session_state["deleted_review_save_fingerprint"] is None
    assert app.button(key="save_review").disabled is True
    assert "Review saved automatically" in "\n".join(
        item.value for item in app.success
    )


def test_unchanged_authoritative_review_does_not_autosave_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = analyzed_demo(new_app())

    with patch("scopeproof_core.storage.json_store.JsonReviewStore.save") as save:
        app = app.run()

    save.assert_not_called()


@pytest.mark.parametrize(
    ("widget_collection", "key", "value"),
    [
        ("text_input", "criterion_text_AC-01", "Pending revised requirement"),
        ("text_input", "new_criterion_text", "Pending additional criterion"),
        ("text_area", "requirements_input", "Pending source requirement"),
        (
            "text_input",
            "runtime_artifact_reference",
            "pending-runtime-artifact",
        ),
    ],
)
def test_pending_draft_categories_block_autosave(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    widget_collection: str,
    key: str,
    value: str,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    store = JsonReviewStore(default_local_review_directory())
    persisted_before = store.load(review_id)
    app.session_state["saved_review_fingerprint"] = None

    with patch("scopeproof_core.storage.json_store.JsonReviewStore.save") as save:
        widget = getattr(app, widget_collection)(key=key)
        app = widget.set_value(value).run()

    save.assert_not_called()
    assert store.load(review_id) == persisted_before
    assert all(button.disabled for button in app.download_button)


def test_delete_saved_review_requires_selection_and_confirmation_and_deletes_only_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, first_review_id = saved_demo_review(new_app())
    _, second_review_id = saved_demo_review(new_app())

    app = new_app()
    assert not [item for item in app.button if item.key == "delete_saved_review"]
    assert not [
        item
        for item in app.checkbox
        if item.key == "delete_saved_review_confirmed"
    ]

    app = select_saved_review(app, first_review_id)
    assert app.checkbox(key="delete_saved_review_confirmed").value is False
    assert app.button(key="delete_saved_review").disabled is True

    app = app.checkbox(key="delete_saved_review_confirmed").check().run()
    assert app.button(key="delete_saved_review").disabled is False
    app = app.button(key="delete_saved_review").click().run()

    assert app.selectbox(key="saved_reopen_review_id").options == [second_review_id]
    assert app.selectbox(key="saved_reopen_review_id").value is None
    assert app.session_state["delete_saved_review_confirmed"] is False


def test_delete_selected_saved_review_preserves_other_open_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, first_review_id = saved_demo_review(new_app())
    _, second_review_id = saved_demo_review(new_app())
    app = select_saved_review(new_app(), first_review_id)
    app = app.button(key="reopen_review").click().run()
    open_state = app.session_state["review_state"]
    saved_fingerprint = app.session_state["saved_review_fingerprint"]
    deleted_fingerprint = app.session_state["deleted_review_save_fingerprint"]

    app = select_saved_review(app, second_review_id)
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()
    app = app.button(key="delete_saved_review").click().run()

    assert app.session_state["review_state"] == open_state
    assert app.session_state["saved_review_fingerprint"] == saved_fingerprint
    assert (
        app.session_state["deleted_review_save_fingerprint"]
        == deleted_fingerprint
    )
    assert app.selectbox(key="saved_reopen_review_id").options == [first_review_id]
    assert second_review_id not in app.selectbox(key="saved_reopen_review_id").options


def test_delete_saved_review_controls_stay_hidden_for_manually_typed_missing_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = new_app()

    app = app.text_input(key="reopen_review_id").set_value("missing-review").run()

    assert not [
        item
        for item in app.checkbox
        if item.key == "delete_saved_review_confirmed"
    ]
    assert not [item for item in app.button if item.key == "delete_saved_review"]


def test_delete_saved_open_review_preserves_exact_state_as_unsaved_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())
    app = select_saved_review(new_app(), review_id)
    app = app.button(key="reopen_review").click().run()
    open_state = app.session_state["review_state"]

    app = select_saved_review(app, review_id)
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()
    app = app.button(key="delete_saved_review").click().run()

    assert app.session_state["review_state"] == open_state
    assert app.session_state["saved_review_fingerprint"] is None
    assert app.session_state["deleted_review_save_fingerprint"] == (
        _review_fingerprint_for_test(open_state)
    )
    with pytest.raises(FileNotFoundError):
        JsonReviewStore(default_local_review_directory()).load(review_id)
    assert (
        "Saved review deleted. The open review remains available as unsaved work."
        in [message.value for message in app.success]
    )

    app = app.run()

    with pytest.raises(FileNotFoundError):
        JsonReviewStore(default_local_review_directory()).load(review_id)
    assert app.session_state["saved_review_fingerprint"] is None
    assert app.session_state["deleted_review_save_fingerprint"] == (
        _review_fingerprint_for_test(open_state)
    )


def test_save_now_recreates_deleted_open_review_and_clears_suppression(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())
    app = select_saved_review(new_app(), review_id)
    app = app.button(key="reopen_review").click().run()
    open_state = app.session_state["review_state"]
    app = select_saved_review(app, review_id)
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()
    app = app.button(key="delete_saved_review").click().run()
    app = app.run()

    assert app.button(key="save_review").label == "Save now"
    assert app.button(key="save_review").disabled is False
    app = app.button(key="save_review").click().run()

    assert JsonReviewStore(default_local_review_directory()).load(review_id) == open_state
    assert app.session_state["saved_review_fingerprint"] == (
        _review_fingerprint_for_test(open_state)
    )
    assert app.session_state["failed_review_save_fingerprint"] is None
    assert app.session_state["deleted_review_save_fingerprint"] is None


def test_new_resolution_after_delete_changes_fingerprint_and_autosaves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())
    app = select_saved_review(new_app(), review_id)
    app = app.button(key="reopen_review").click().run()
    deleted_state = app.session_state["review_state"]
    deleted_fingerprint = _review_fingerprint_for_test(deleted_state)
    app = select_saved_review(app, review_id)
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()
    app = app.button(key="delete_saved_review").click().run()

    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.ACCEPTED
    ).run()
    app = app.button(key="save_resolution").click().run()
    app = app.run()

    revised_state = app.session_state["review_state"]
    revised_fingerprint = _review_fingerprint_for_test(revised_state)
    assert revised_fingerprint != deleted_fingerprint
    assert JsonReviewStore(default_local_review_directory()).load(review_id) == revised_state
    assert app.session_state["saved_review_fingerprint"] == revised_fingerprint
    assert app.session_state["failed_review_save_fingerprint"] is None
    assert app.session_state["deleted_review_save_fingerprint"] is None


def test_reopening_unchanged_review_does_not_rewrite_local_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())
    app = select_saved_review(new_app(), review_id)

    with patch("scopeproof_core.storage.json_store.JsonReviewStore.save") as save:
        app = app.button(key="reopen_review").click().run()

    save.assert_not_called()
    assert app.session_state["saved_review_fingerprint"] == (
        _review_fingerprint_for_test(app.session_state["review_state"])
    )


def test_delete_saved_review_race_uses_fixed_recovery_without_raw_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())
    app = select_saved_review(new_app(), review_id)
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()

    with patch(
        "scopeproof_core.storage.json_store.JsonReviewStore.delete",
        side_effect=FileNotFoundError(review_id),
    ):
        app = app.button(key="delete_saved_review").click().run()

    recovery = (
        "The selected saved review was already removed. Refresh the saved review list."
    )
    assert recovery in [message.value for message in app.warning]
    assert not app.exception
    rendered_recovery = "\n".join(
        message.value for message in [*app.warning, *app.error]
    )
    assert str(tmp_path) not in rendered_recovery


def test_open_review_delete_race_records_suppression_and_exposes_save_now(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    state = app.session_state["review_state"]
    fingerprint = _review_fingerprint_for_test(state)
    app = select_saved_review(app, review_id)
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()
    JsonReviewStore(default_local_review_directory()).delete(review_id)

    with patch(
        "scopeproof_core.storage.json_store.JsonReviewStore.list_review_ids",
        return_value=[review_id],
    ):
        app = app.button(key="delete_saved_review").click().run()

    assert app.session_state["review_state"] == state
    assert app.session_state["saved_review_fingerprint"] is None
    assert app.session_state["failed_review_save_fingerprint"] is None
    assert app.session_state["deleted_review_save_fingerprint"] == fingerprint
    with pytest.raises(FileNotFoundError):
        JsonReviewStore(default_local_review_directory()).load(review_id)

    app = app.run()

    with pytest.raises(FileNotFoundError):
        JsonReviewStore(default_local_review_directory()).load(review_id)
    assert app.button(key="save_review").label == "Save now"
    assert app.button(key="save_review").disabled is False


def test_symlinked_review_store_has_safe_recovery_and_disables_storage_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    outside = tmp_path / "outside"
    outside.mkdir()
    store_parent = tmp_path / ".scopeproof"
    store_parent.mkdir()
    (store_parent / "reviews").symlink_to(outside, target_is_directory=True)

    app = new_app()

    assert [item.value for item in app.error] == [
        "Local review storage is unavailable. Verify that the ScopeProof review directory "
        "is a regular local directory."
    ]
    assert not [item for item in app.text_input if item.key == "reopen_review_id"]
    assert not [item for item in app.selectbox if item.key == "saved_reopen_review_id"]
    assert app.button(key="reopen_review").disabled is True

    with patch("scopeproof_core.storage.json_store.JsonReviewStore.save") as save:
        app = analyzed_demo(app)

    save.assert_not_called()
    review_state = app.session_state["review_state"].model_copy(deep=True)
    recovery = (
        "Local saving is unavailable. The current review remains open as unsaved work, "
        "and exports remain available. Verify that the ScopeProof review directory is a "
        "regular local directory; ScopeProof will recheck it on the next interaction."
    )

    assert recovery in [item.value for item in app.warning]
    assert app.button(key="save_review").disabled is True
    assert app.session_state["review_state"] == review_state
    assert app.session_state["saved_review_fingerprint"] is None
    assert len(app.download_button) == 3
    rendered_recovery = "\n".join(
        item.value
        for item in [
            *app.error,
            *app.warning,
            *app.info,
            *app.success,
        ]
    )
    assert str(tmp_path) not in rendered_recovery
    assert list(outside.iterdir()) == []

    app = app.text_input(key="runtime_artifact_reference").set_value(
        "pending-runtime-artifact"
    ).run()
    pending_recovery = (
        "Local saving is unavailable. The current review remains open as unsaved work, "
        "and exports remain unavailable until pending review inputs are confirmed, "
        "submitted, discarded, or cleared. Verify that the ScopeProof review directory "
        "is a regular local directory; ScopeProof will recheck it on the next interaction."
    )
    assert pending_recovery in [item.value for item in app.warning]
    assert all(button.disabled for button in app.download_button)


def test_regular_file_review_store_has_safe_recovery_and_disables_storage_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    store_parent = tmp_path / ".scopeproof"
    store_parent.mkdir()
    store_root = store_parent / "reviews"
    store_root.write_text("not a directory", encoding="utf-8")

    app = new_app()

    assert [item.value for item in app.error] == [
        "Local review storage is unavailable. Verify that the ScopeProof review directory "
        "is a regular local directory."
    ]
    assert not [item for item in app.text_input if item.key == "reopen_review_id"]
    assert not [item for item in app.selectbox if item.key == "saved_reopen_review_id"]
    assert app.button(key="reopen_review").disabled is True

    with patch("scopeproof_core.storage.json_store.JsonReviewStore.save") as save:
        app = analyzed_demo(app)

    save.assert_not_called()
    assert app.button(key="save_review").disabled is True
    assert store_root.read_text(encoding="utf-8") == "not a directory"


def test_blank_public_pr_url_remains_neutral_and_disables_fetch() -> None:
    app = new_app()

    warning_text = "\n".join(item.value for item in app.warning)
    assert "Enter a public GitHub pull request URL" not in warning_text
    assert app.button(key="fetch_pr").disabled is True


def test_explicit_candidate_paths_are_normalized_and_fetched() -> None:
    app = new_app()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/widget/pull/42"
    ).run()
    app = app.text_area(key="candidate_paths").set_value(
        " src/context.py\n\ndocs/requirements.md\nsrc/context.py "
    ).run()
    snapshot = load_demo_snapshot().model_copy(
        update={"repository": "acme/widget", "pr_number": 42}
    )

    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            return_value=snapshot,
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
            return_value=[],
        ) as fetch_candidates,
    ):
        app = app.button(key="fetch_pr").click().run()

    fetch_candidates.assert_called_once_with(
        "acme/widget",
        snapshot.head_sha,
        ["src/context.py", "docs/requirements.md"],
    )
    assert app.session_state["candidate_files"] == []


def test_first_use_flow_labels_five_stages_and_defaults_to_standard_review() -> None:
    app = new_app()

    visible = "\n".join(
        item.value for item in [*app.markdown, *app.caption, *app.info]
    )
    assert (
        "Public PR → Confirm criteria → Review coverage → Record decisions → Export"
        in visible
    )
    assert app.checkbox(key="alpha_feedback_mode").value is False
    assert "does not create participant research records" in visible


def test_confirmed_alpha_fetch_requires_validated_public_safe_preflight() -> None:
    app = new_app()
    app = app.checkbox(key="alpha_feedback_mode").check().run()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/widget/pull/42"
    ).run()

    assert app.button(key="fetch_pr").disabled is True

    app = app.text_input(key="requirements_source_url").set_value(
        "https://github.com/acme/widget/issues/41"
    ).run()
    app = app.checkbox(key="source_owner_confirmed").check().run()
    app = app.checkbox(key="no_confidential_information").check().run()

    assert app.selectbox(key="participant_role").value == "product_manager"
    assert app.button(key="fetch_pr").disabled is False


def test_criteria_and_outcome_surfaces_preserve_human_confirmation_boundary() -> None:
    app = analyzed_demo(new_app())
    visible = "\n".join(
        item.value
        for item in [*app.markdown, *app.caption, *app.info, *app.code]
    )

    assert "source owner" in visible.lower()
    assert "Participant outcome" not in visible
    assert not [item for item in app.selectbox if item.key == "alpha_outcome"]
    selected = app.selectbox(key="selected_criterion").value
    expected_action = next(
        finding.recommended_action
        for finding in app.session_state["bundle"].findings
        if finding.criterion_id == selected
    )
    assert expected_action in [item.value for item in app.code]


def test_malformed_public_pr_url_shows_format_guidance_and_disables_fetch() -> None:
    app = new_app()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/widget/pull/not-a-number"
    ).run()

    warning_text = "\n".join(item.value for item in app.warning)
    assert (
        "Enter a public GitHub pull request URL in this format: "
        "`https://github.com/OWNER/REPO/pull/NUMBER`."
    ) in warning_text
    assert app.button(key="fetch_pr").disabled is True


def test_canonical_public_pr_url_enables_fetch_without_format_warning() -> None:
    app = new_app()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/widget/pull/42"
    ).run()

    warning_text = "\n".join(item.value for item in app.warning)
    assert "Enter a public GitHub pull request URL" not in warning_text
    assert app.button(key="fetch_pr").disabled is False


@pytest.mark.parametrize(
    "fetch_error",
    [
        GitHubNetworkError("Could not reach GitHub."),
        GitHubPaginationError("GitHub pagination target was rejected."),
    ],
)
def test_public_pr_fetch_failure_preserves_inputs_and_shows_retry_guidance(
    fetch_error: Exception,
) -> None:
    requirement = "The export error state remains visible and retryable."
    app = new_app()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/widget/pull/42"
    ).run()
    app = app.text_area(key="requirements_input").set_value(requirement).run()
    app = app.button(key="prepare_criteria").click().run()

    with patch(
        "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
        side_effect=fetch_error,
    ):
        app = app.button(key="fetch_pr").click().run()

    rendered_errors = "\n".join(item.value for item in app.error)
    assert str(fetch_error) in rendered_errors
    assert "No review data was changed." in rendered_errors
    assert "Verify that the PR is public and try again." in rendered_errors
    assert app.text_input(key="pr_url").value == "https://github.com/acme/widget/pull/42"
    assert app.text_area(key="requirements_input").value == requirement
    assert [criterion.text for criterion in app.session_state["criteria"]] == [requirement]
    assert app.button(key="fetch_pr").disabled is False


def test_loaded_public_pr_shows_validated_source_identity_before_criteria_confirmation() -> None:
    head_sha = "0123456789abcdef0123456789abcdef01234567"
    snapshot = load_demo_snapshot().model_copy(
        update={
            "repository": "acme/widget",
            "pr_number": 7,
            "head_sha": head_sha,
            "ingestion_state": IngestionState.COMPLETE,
        }
    )
    app = new_app()
    app = (
        app.text_input(key="pr_url").set_value("https://github.com/operator/entered/pull/42").run()
    )

    with patch(
        "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
        return_value=snapshot,
    ):
        app = app.button(key="fetch_pr").click().run()

    text_values = [item.value for item in app.text]
    code_text = "\n".join(item.value for item in app.code)
    caption_text = "\n".join(item.value for item in app.caption)
    assert "acme/widget · PR #7" in text_values
    assert head_sha in code_text
    assert "2 changed files fetched" in caption_text
    assert "Complete ingestion" in caption_text
    assert app.button(key="run_analysis").disabled is True

    app = (
        app.text_area(key="requirements_input")
        .set_value("The loaded source identity remains visible while criteria are edited.")
        .run()
    )

    text_values = [item.value for item in app.text]
    code_text = "\n".join(item.value for item in app.code)
    caption_text = "\n".join(item.value for item in app.caption)
    assert "acme/widget · PR #7" in text_values
    assert "operator/entered · PR #42" not in text_values
    assert head_sha in code_text
    assert "2 changed files fetched" in caption_text
    assert "Complete ingestion" in caption_text
    assert app.button(key="run_analysis").disabled is True


def test_demo_loads_confirmable_criteria() -> None:
    app = load_demo(new_app())
    assert app.session_state["snapshot"] is not None
    assert app.session_state["criteria_confirmed"] is False
    assert len(app.text_input) >= 4
    assert app.button(key="confirm_criteria").disabled is False


def test_demo_marks_requirements_prepared_and_exposes_confirmation_link() -> None:
    app = load_demo(new_app())

    assert app.button(key="prepare_criteria").disabled is True
    assert "Criteria prepared. Review the set before explicitly confirming it." in [
        item.value for item in app.success
    ]
    assert "[Continue to 2 · Confirm Criteria](#2-confirm-criteria)" in [
        item.value for item in app.markdown
    ]
    assert app.session_state["criteria_confirmed"] is False
    assert app.button(key="run_analysis").disabled is True


def test_editing_prepared_requirements_reenables_preparation() -> None:
    app = load_demo(new_app())
    app = app.text_area(key="requirements_input").set_value(
        "Users can export the currently filtered list as CSV."
    ).run()

    assert app.button(key="prepare_criteria").disabled is False
    assert "Criteria prepared. Review the set before explicitly confirming it." not in [
        item.value for item in app.success
    ]
    assert "[Continue to 2 · Confirm Criteria](#2-confirm-criteria)" not in [
        item.value for item in app.markdown
    ]


def test_criteria_confirmation_explains_required_evidence_levels() -> None:
    app = load_demo(new_app())
    caption_text = "\n".join(item.value for item in app.caption)

    assert (
        "Evidence levels set the minimum proof needed for each criterion: "
        "E1 = implementation or contract candidate; E2 = test candidate; "
        "E3 = manually recorded runtime verification. Static PR analysis can produce "
        "only E1 or E2."
    ) in caption_text


def test_evidence_matrix_explains_observed_evidence_levels() -> None:
    app = analyzed_demo(new_app())
    caption_text = "\n".join(item.value for item in app.caption)

    assert (
        "Evidence status describes deterministic candidates, not correctness. Evidence types "
        "keep implementation, test, and externally recorded runtime observations separate."
    ) in caption_text


def test_sidebar_reports_confirmation_and_next_action_in_same_run() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()

    sidebar_text = "\n".join(markdown.value for markdown in app.sidebar.markdown)
    assert "Complete — Criteria confirmed" in sidebar_text
    assert "Next — Run deterministic analysis" in sidebar_text
    assert "active_step" not in app.session_state.filtered_state


def test_criteria_confirmation_shows_one_durable_success_message() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()

    assert [item.value for item in app.success] == [
        "Criteria confirmed by the reviewer."
    ]
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Complete — Criteria confirmed" in sidebar_text
    assert "Next — Run deterministic analysis" in sidebar_text
    assert app.button(key="run_analysis").disabled is False


def test_analysis_continuation_link_tracks_confirmed_transition() -> None:
    continuation_link = (
        "[Continue to run deterministic analysis](#run-deterministic-analysis)"
    )
    app = load_demo(new_app())

    assert continuation_link not in [item.value for item in app.markdown]

    app = app.button(key="confirm_criteria").click().run()

    assert continuation_link in [item.value for item in app.markdown]
    assert "### Run deterministic analysis" in [item.value for item in app.markdown]

    app = app.text_input(key="criterion_text_AC-01").set_value(
        "Changed visible criterion"
    ).run()

    assert continuation_link not in [item.value for item in app.markdown]

    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    assert continuation_link not in [item.value for item in app.markdown]


def test_sidebar_reports_analysis_and_review_availability() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    sidebar_text = "\n".join(markdown.value for markdown in app.sidebar.markdown)
    assert "Complete — Analysis generated" in sidebar_text
    assert "Available — Review evidence and export" in sidebar_text
    assert "Complete — Review and export available" not in sidebar_text


@pytest.mark.parametrize(
    ("existing_review", "transition_name"),
    [(False, "new_review_state"), (True, "attach_analysis")],
)
def test_analysis_transition_failure_preserves_retryable_state_without_raw_details(
    existing_review: bool,
    transition_name: str,
) -> None:
    if existing_review:
        app = analyzed_demo(new_app())
        app = app.text_input(key="criterion_text_AC-01").set_value(
            "User can export the revised research list as CSV"
        ).run()
        app = app.button(key="confirm_criteria").click().run()
    else:
        app = load_demo(new_app())
        app = app.button(key="confirm_criteria").click().run()
    current_state = app.session_state["review_state"]
    review_state = current_state.model_copy(deep=True) if current_state is not None else None
    bundle = app.session_state["bundle"]
    source_reload_notice = app.session_state["source_reload_notice"]
    raw_error = f"invalid analysis transition at /private/secret/{transition_name}.json"

    with patch(
        f"scopeproof_core.reviews.lifecycle.{transition_name}",
        side_effect=ValueError(raw_error),
    ):
        app = app.button(key="run_analysis").click().run()

    recovery = (
        "Analysis could not be completed. No review state was changed. Verify the confirmed "
        "criteria and loaded source, then try again."
    )
    assert recovery in [item.value for item in app.error]
    assert not app.exception
    rendered = "\n".join(
        item.value
        for item in [
            *app.error,
            *app.warning,
            *app.info,
            *app.success,
            *app.caption,
            *app.markdown,
            *app.code,
        ]
    )
    assert raw_error not in rendered
    assert "/private/secret/" not in rendered
    assert app.session_state["review_state"] == review_state
    assert app.session_state["bundle"] == bundle
    assert app.session_state["source_reload_notice"] == source_reload_notice
    assert app.session_state["criteria_confirmed"] is True
    assert app.button(key="run_analysis").disabled is False
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Complete — Analysis generated" not in sidebar_text


@pytest.mark.parametrize("transition_name", ["revise_criteria", "confirm_criteria"])
def test_criteria_confirmation_failure_preserves_pending_edit_without_raw_details(
    transition_name: str,
) -> None:
    app = analyzed_demo(new_app())
    edited_text = "User can export the safely revised research list as CSV"
    app = app.text_input(key="criterion_text_AC-01").set_value(edited_text).run()
    review_state = app.session_state["review_state"].model_copy(deep=True)
    criteria = list(app.session_state["criteria"])
    bundle = app.session_state["bundle"].model_copy(deep=True)
    raw_error = f"invalid criteria transition at /private/secret/{transition_name}.json"

    with patch(
        f"scopeproof_core.reviews.lifecycle.{transition_name}",
        side_effect=ValueError(raw_error),
    ):
        app = app.button(key="confirm_criteria").click().run()

    recovery = (
        "Criteria could not be confirmed. The current review remains unchanged. Verify the "
        "edited criteria and try again."
    )
    assert recovery in [item.value for item in app.error]
    assert not app.exception
    rendered = "\n".join(
        item.value
        for item in [
            *app.error,
            *app.warning,
            *app.info,
            *app.success,
            *app.caption,
            *app.markdown,
            *app.code,
        ]
    )
    assert raw_error not in rendered
    assert "/private/secret/" not in rendered
    assert app.session_state["review_state"] == review_state
    assert app.session_state["criteria"] == criteria
    assert app.session_state["bundle"] == bundle
    assert app.session_state["criteria_confirmed"] is True
    assert app.text_input(key="criterion_text_AC-01").value == edited_text
    assert app.button(key="confirm_criteria").disabled is False
    assert app.button(key="run_analysis").disabled is True


@pytest.mark.parametrize(
    ("operation_name", "button_key", "input_key", "input_value"),
    [
        (
            "add_criterion",
            "add_criterion_ui",
            "new_criterion_text",
            "Document the export format",
        ),
        (
            "split_criterion",
            "split_criterion_ui",
            "split_criterion_text",
            "Export CSV\nRecord analytics",
        ),
        ("remove_criterion", "remove_AC-01", None, None),
        ("reorder_criteria", "move_up_AC-02", None, None),
    ],
)
def test_criteria_edit_failure_preserves_review_and_retry_without_raw_details(
    operation_name: str,
    button_key: str,
    input_key: str | None,
    input_value: str | None,
) -> None:
    app = analyzed_demo(new_app())
    if input_key is not None and input_value is not None:
        widget = (
            app.text_area(key=input_key)
            if input_key == "split_criterion_text"
            else app.text_input(key=input_key)
        )
        app = widget.set_value(input_value).run()
    review_state = app.session_state["review_state"].model_copy(deep=True)
    bundle = app.session_state["bundle"].model_copy(deep=True)
    criteria = [item.model_copy(deep=True) for item in app.session_state["criteria"]]
    raw_error = f"invalid criteria edit at /private/secret/{operation_name}.json"

    with patch(
        f"scopeproof_core.criteria.service.{operation_name}",
        side_effect=ValueError(raw_error),
    ):
        app = app.button(key=button_key).click().run()

    recovery = (
        "Criteria could not be updated. The current review remains unchanged. Verify the edit "
        "and try again."
    )
    assert recovery in [item.value for item in app.error]
    assert not app.exception
    rendered = "\n".join(
        item.value
        for item in [
            *app.error,
            *app.warning,
            *app.info,
            *app.success,
            *app.caption,
            *app.markdown,
            *app.code,
        ]
    )
    assert raw_error not in rendered
    assert "/private/secret/" not in rendered
    assert app.session_state["review_state"] == review_state
    assert app.session_state["bundle"] == bundle
    assert app.session_state["criteria"] == criteria
    assert app.session_state["criteria_confirmed"] is True
    assert app.session_state["replace_unsaved_review_confirmed"] is False
    if input_key is not None and input_value is not None:
        widget = (
            app.text_area(key=input_key)
            if input_key == "split_criterion_text"
            else app.text_input(key=input_key)
        )
        assert widget.value == input_value
    assert app.button(key=button_key).disabled is False


def test_sidebar_step_navigation_links_next_action_and_keeps_locked_steps_plain() -> None:
    app = new_app()

    assert [item.value for item in app.sidebar.markdown] == [
        "**Review status**",
        "[Next — Load a public PR or demo](#1-start-review)",
        "Locked — Prepare at least one criterion",
        "Locked — Confirm criteria",
        "Locked — Run deterministic analysis",
        "Locked — Review and export",
    ]


def test_sidebar_step_navigation_tracks_available_workflow_sections() -> None:
    app = load_demo(new_app())

    assert [item.value for item in app.sidebar.markdown] == [
        "**Review status**",
        "[Complete — Source loaded](#1-start-review)",
        "[Complete — Criteria prepared](#2-confirm-criteria)",
        "[Next — Confirm criteria](#2-confirm-criteria)",
        "Locked — Run deterministic analysis",
        "Locked — Review and export",
    ]

    app = app.button(key="confirm_criteria").click().run()

    assert [item.value for item in app.sidebar.markdown] == [
        "**Review status**",
        "[Complete — Source loaded](#1-start-review)",
        "[Complete — Criteria prepared](#2-confirm-criteria)",
        "[Complete — Criteria confirmed](#2-confirm-criteria)",
        "[Next — Run deterministic analysis](#run-deterministic-analysis)",
        "Locked — Review and export",
    ]

    app = app.button(key="run_analysis").click().run()

    assert [item.value for item in app.sidebar.markdown] == [
        "**Review status**",
        "[Complete — Source loaded](#1-start-review)",
        "[Complete — Criteria prepared](#2-confirm-criteria)",
        "[Complete — Criteria confirmed](#2-confirm-criteria)",
        "[Complete — Analysis generated](#3-decision-progress)",
        "Available — Review evidence and export",
    ]


def test_sidebar_uses_active_review_ruleset_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    current_caption = (
        f"Ruleset {RULESET_VERSION} · local-first · public repositories only"
    )
    assert current_caption in [item.value for item in new_app().sidebar.caption]

    saved, review_id = saved_demo_review(new_app())
    current_state = saved.session_state["review_state"]
    historical_review = current_state.review.model_copy(
        update={"ruleset_version": "0.9.0"}
    )
    historical_bundle = current_state.bundle.model_copy(
        update={"review": historical_review}
    )
    historical_state = current_state.model_copy(
        update={"review": historical_review, "bundle": historical_bundle}
    )
    JsonReviewStore(default_local_review_directory()).save(historical_state)

    reopened = select_saved_review(new_app(), review_id)
    reopened = reopened.button(key="reopen_review").click().run()

    assert (
        "Ruleset 0.9.0 · local-first · public repositories only"
        in [item.value for item in reopened.sidebar.caption]
    )


def test_criteria_summary_and_confirmation_precede_long_editor_list() -> None:
    app = load_demo(new_app())
    keys = _main_widget_keys(app)
    visible = "\n".join(item.value for item in [*app.caption, *app.markdown])

    assert keys.count("confirm_criteria") == 1
    assert keys.index("confirm_criteria") < keys.index("criterion_text_AC-01")
    assert keys.index("confirm_criteria") < keys.index("new_criterion_text")
    assert "Criteria: 4" in visible
    assert "Confirmation: Required" in visible
    assert "Pending edits: None" in visible


def test_criterion_editors_are_collapsed_and_keep_requirement_text_inert() -> None:
    app = load_demo(new_app())
    criterion_expanders = [item for item in app.expander if item.label.startswith("AC-")]

    assert [item.label for item in criterion_expanders] == [
        "AC-01 · Must Have · E1",
        "AC-02 · Must Have · E1",
        "AC-03 · Must Have · E1",
        "AC-04 · Should Have · E1",
    ]
    assert all(item.proto.expanded is False for item in criterion_expanders)
    for criterion, expander in zip(app.session_state["criteria"], criterion_expanders, strict=True):
        assert criterion.text in [item.value for item in expander.text]
        assert criterion.text not in expander.label


def test_add_and_split_controls_are_one_collapsed_secondary_group() -> None:
    app = load_demo(new_app())
    editor = next(item for item in app.expander if item.label == "Add or split criteria")
    child_keys = _main_widget_keys(editor)

    assert editor.proto.expanded is False
    assert child_keys == [
        "new_criterion_text",
        "add_criterion_ui",
        "split_criterion_id",
        "split_criterion_text",
        "split_criterion_ui",
    ]


def test_markdown_shaped_confirmed_requirement_remains_inert() -> None:
    unsafe_text = "![criterion](https://example.invalid/criterion.png)"
    app = load_demo(new_app())
    app = app.text_input(key="criterion_text_AC-01").set_value(unsafe_text).run()
    app = app.button(key="confirm_criteria").click().run()

    assert unsafe_text in [item.value for item in app.text]
    assert all(unsafe_text not in item.label for item in app.expander)
    assert all(unsafe_text not in item.value for item in app.markdown)


def test_markdown_shaped_selected_requirement_remains_inert_in_detail_contexts() -> None:
    unsafe_text = "![criterion](https://example.invalid/criterion.png)"
    app = load_demo(new_app())
    app = app.text_input(key="criterion_text_AC-01").set_value(unsafe_text).run()
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    assert unsafe_text in [item.value for item in app.text]
    assert all(unsafe_text not in item.value for item in app.caption)
    assert all(unsafe_text not in item.value for item in app.markdown)


@pytest.mark.parametrize("text", ["", "   ", "\t\n"])
def test_blank_criterion_edit_stays_recoverable_and_cannot_be_confirmed(text: str) -> None:
    app = analyzed_demo(new_app())
    confirmed_text = app.session_state["criteria"][0].text

    app = app.text_input(key="criterion_text_AC-01").set_value(text).run()

    assert not app.exception
    assert app.session_state["criteria"][0].text == confirmed_text
    assert app.button(key="confirm_criteria").disabled is True
    assert app.button(key="run_analysis").disabled is True
    assert "AC-01: Criterion text cannot be blank." in [
        item.value for item in app.warning
    ]
    criterion_editor = next(item for item in app.expander if item.label.startswith("AC-01"))
    assert "Criterion text cannot be blank." in [
        item.value for item in criterion_editor.warning
    ]


def test_confirmed_criteria_disable_repeat_confirmation_until_an_edit() -> None:
    app = analyzed_demo(new_app())
    state_before = app.session_state["review_state"].model_copy(deep=True)

    assert app.button(key="confirm_criteria").disabled is True
    assert state_before.criteria_revision.number == 1
    assert state_before.bundle is not None

    app = app.text_input(key="criterion_text_AC-01").set_value(
        "Changed visible criterion"
    ).run()

    assert app.button(key="confirm_criteria").disabled is False
    assert app.session_state["review_state"] == state_before


def test_pending_criterion_text_edit_requires_reconfirmation_before_analysis() -> None:
    app = analyzed_demo(new_app())
    confirmed_text = app.session_state["criteria"][0].text

    app = app.text_input(key="criterion_text_AC-01").set_value(
        "Changed visible criterion"
    ).run()

    assert app.text_input(key="criterion_text_AC-01").value == "Changed visible criterion"
    assert app.session_state["criteria"][0].text == confirmed_text
    assert app.session_state["bundle"].criteria[0].text == confirmed_text
    assert app.button(key="run_analysis").disabled is True
    assert (
        "Criteria edits are pending confirmation. Visible evidence and verdict still use "
        "the last confirmed criteria. Confirm the updated set before rerunning analysis."
    ) in [item.value for item in app.warning]
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Next — Confirm updated criteria" in sidebar_text
    assert "Complete — Criteria confirmed" not in sidebar_text

    app = app.button(key="confirm_criteria").click().run()

    assert app.session_state["criteria"][0].text == "Changed visible criterion"
    assert app.session_state["criteria_confirmed"] is True
    confirmed_revision = app.session_state["review_state"].criteria_revision
    assert confirmed_revision.confirmed_at is not None
    assert confirmed_revision.confirmed_at >= confirmed_revision.created_at
    assert app.session_state["review_state"].bundle is None
    assert app.session_state["bundle"] is None
    assert app.button(key="run_analysis").disabled is False
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Complete — Criteria confirmed" in sidebar_text
    assert "Next — Run deterministic analysis" in sidebar_text


def test_pending_criterion_priority_edit_uses_same_confirmation_boundary() -> None:
    app = analyzed_demo(new_app())

    app = app.selectbox(key="criterion_priority_AC-01").set_value(
        Priority.SHOULD_HAVE
    ).run()

    assert app.session_state["criteria"][0].priority is Priority.MUST_HAVE
    assert app.session_state["bundle"].criteria[0].priority is Priority.MUST_HAVE
    assert app.button(key="run_analysis").disabled is True
    assert "Next — Confirm updated criteria" in "\n".join(
        item.value for item in app.sidebar.markdown
    )


def test_demo_flow_reaches_blocked_summary() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    assert app.session_state["criteria_confirmed"] is True
    app = app.button(key="run_analysis").click().run()
    visible_text = "\n".join(markdown.value for markdown in app.markdown)
    evidence_statuses = {item.value for item in app.caption}
    assert "Action required" in visible_text
    assert "Evidence status: Weak candidate" in evidence_statuses
    assert "Evidence status: No candidate" in evidence_statuses
    assert app.session_state["bundle"] is not None


def test_demo_summary_explains_non_prescriptive_next_actions() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    visible_text = "\n".join(
        item.value for item in [*app.markdown, *app.text]
    )
    assert "What to do next" in visible_text
    assert "unresolved criteria: AC-01" in visible_text


def test_evidence_matrix_has_compact_strength_summary_and_unresolved_queue() -> None:
    app = analyzed_demo(new_app())
    visible_text = "\n".join(
        item.value for item in [*app.markdown, *app.caption, *app.info, *app.text]
    )

    assert "Candidate strength:" in visible_text
    assert "Strong" in visible_text
    assert "Weak" in visible_text
    assert "None" in visible_text
    assert "Unresolved criteria queue" in visible_text
    assert "Decisions recorded: 0 of 4" in visible_text
    assert "Review candidate evidence and record an explicit human decision" in visible_text
    assert "ScopeProof does not decide them" in visible_text
    assert "Gate reasons: Blocking Criteria" in visible_text

    captions = [item.value for item in app.caption]
    assert captions.index("Decisions recorded: 0 of 4.") < next(
        index for index, value in enumerate(captions) if value.startswith("Observed CI:")
    )
    markdown = [item.value for item in app.markdown]
    assert "[Review AC-01](#review-ac-01)" in markdown
    assert "#### Review AC-01" in markdown
    assert app.button(key="inspect_queue_AC-02").label == (
        "Open AC-02 decision controls"
    )
    queue_keys = [
        button.key
        for button in app.button
        if button.key is not None and button.key.startswith("inspect_queue_")
    ]
    assert queue_keys == [
        "inspect_queue_AC-02",
        "inspect_queue_AC-03",
        "inspect_queue_AC-01",
        "inspect_queue_AC-04",
    ]

    main_nodes = list(app.main)
    node_positions = {
        node.key: index
        for index, node in enumerate(main_nodes)
        if node.key
        in {
            "inspect_queue_AC-02",
            "selected_criterion",
            "resolution_decision",
            "status_filter",
        }
    }
    assert node_positions["inspect_queue_AC-02"] < node_positions["selected_criterion"]
    assert node_positions["selected_criterion"] < node_positions["resolution_decision"]
    assert node_positions["resolution_decision"] < node_positions["status_filter"]

    app = app.button(key="inspect_queue_AC-02").click().run()

    assert app.selectbox(key="selected_criterion").value == "AC-02"


def test_summary_offers_direct_next_unresolved_action() -> None:
    app = analyzed_demo(new_app())

    assert "[Review next unresolved criterion](#review-ac-02)" in [
        item.value for item in app.markdown
    ]


def test_demo_summary_humanizes_gate_reasons_without_mutating_codes() -> None:
    app = analyzed_demo(new_app())
    markdown_text = "\n".join(item.value for item in app.markdown)

    assert (
        "Gate reasons: Blocking Criteria · Conditional Criteria · Unresolved Criteria"
    ) in markdown_text
    assert "blocking_criteria, conditional_criteria, unresolved_criteria" not in markdown_text
    assert app.session_state["bundle"].gate.reason_codes == [
        "blocking_criteria",
        "conditional_criteria",
        "unresolved_criteria",
    ]


def test_demo_summary_requires_explicit_resolution_decision() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    assert len(app.download_button) == 3
    assert app.selectbox(key="resolution_decision").value is None
    assert app.button(key="save_resolution").disabled is True


def test_decision_reviewer_is_explicit_and_required_for_human_events() -> None:
    app = analyzed_demo(new_app())

    assert app.text_input(key="decision_reviewer").value == "Local reviewer"
    app = app.text_input(key="decision_reviewer").set_value("   ").run()
    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.ACCEPTED
    ).run()

    assert app.button(key="save_resolution").disabled is True
    assert app.button(key="record_final_acceptance").disabled is True
    assert (
        "Decision reviewer is required for an attributable audit event."
        in [item.value for item in app.caption]
    )


def test_human_events_store_the_trimmed_decision_reviewer() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="decision_reviewer").set_value(
        "  Controlled reviewer  "
    ).run()
    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.ACCEPTED
    ).run()
    app = app.button(key="save_resolution").click().run()

    first_event = app.session_state["review_state"].resolution_events[0]
    assert first_event.reviewer == "Controlled reviewer"

    app = resolve_all_criteria(app)
    app = app.button(key="record_final_acceptance").click().run()
    final_event = app.session_state["review_state"].resolution_events[-1]
    assert final_event.final_acceptance is True
    assert final_event.reviewer == "Controlled reviewer"


def test_human_decision_explains_selected_gate_impact() -> None:
    app = analyzed_demo(new_app())
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Select a decision to see its deterministic gate impact." in caption_text

    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.REJECTED_FINDING
    ).run()
    caption_text = "\n".join(item.value for item in app.caption)
    assert (
        "Decision impact: Rejects the provisional finding but does not resolve this criterion; "
        "its finding status continues to control the gate."
    ) in caption_text


def test_optional_token_uses_password_input() -> None:
    app = new_app()
    token = app.text_input(key="github_token")
    assert token.proto.type == token.proto.PASSWORD


def test_demo_can_autosave_and_reopen_durable_review_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    review_id = app.session_state["review_state"].review.review_id

    assert "Review saved automatically" in "\n".join(
        message.value for message in app.success
    )
    app = select_saved_review(app, review_id)
    app = app.button(key="reopen_review").click().run()

    assert app.session_state["review_state"].review.review_id == review_id
    success_text = "\n".join(message.value for message in app.success)
    assert "Review reopened from local storage" in success_text


def test_current_review_id_is_copyable_and_used_in_autosave_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = analyzed_demo(new_app())
    review_id = app.session_state["review_state"].review.review_id

    assert review_id in [item.value for item in app.code]
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Current review ID" in caption_text
    assert "Saved locally — current review matches local storage." in caption_text
    assert app.button(key="save_review").disabled is True
    assert f"Review saved automatically. ID: {review_id}." in [
        item.value for item in app.success
    ]


def test_pending_criterion_draft_is_not_claimed_saved_or_exportable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    authoritative_state = app.session_state["review_state"].model_copy(deep=True)

    app = app.text_input(key="runtime_artifact_reference").set_value(
        "pending-runtime-artifact"
    ).run()
    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.ACCEPTED
    ).run()

    captions = "\n".join(item.value for item in app.caption)
    warnings = "\n".join(item.value for item in app.warning)
    assert "Saved locally — current review matches local storage." not in captions
    assert (
        "Pending criterion-detail inputs are not saved or exported. Submit or clear "
        "them before relying on this review ID."
    ) in captions
    assert (
        "Pending criterion inputs are not part of the review, local save, or exports. "
        "Submit them through the matching form or clear them before continuing."
    ) in warnings
    assert app.button(key="save_review").disabled is True
    assert app.button(key="load_demo").disabled is True
    assert app.checkbox(key="replace_unsaved_review_confirmed").value is False
    assert app.button(key="clear_criterion_detail_drafts").disabled is False
    _assert_pending_draft_preserves_authoritative_review(
        app,
        review_id=review_id,
        authoritative_state=authoritative_state,
    )


def test_clear_pending_criterion_draft_restores_saved_exportable_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, _ = saved_demo_review(new_app())
    review_state = app.session_state["review_state"].model_copy(deep=True)
    app = app.text_input(key="runtime_artifact_reference").set_value(
        "pending-runtime-artifact"
    ).run()
    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.ACCEPTED
    ).run()

    app = app.button(key="clear_criterion_detail_drafts").click().run()

    assert app.session_state["review_state"] == review_state
    assert app.text_input(key="runtime_artifact_reference").value == ""
    assert app.selectbox(key="resolution_decision").value is None
    assert "Pending criterion inputs cleared without changing the review." in [
        item.value for item in app.success
    ]
    captions = "\n".join(item.value for item in app.caption)
    assert "Saved locally — current review matches local storage." in captions
    assert "Pending criterion-detail inputs are not saved or exported." not in captions
    assert app.button(key="save_review").disabled is True
    assert all(not button.disabled for button in app.download_button)
    assert app.button(key="load_demo").disabled is False


def test_submitted_runtime_draft_restores_authoritative_save_and_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/authoritative"
    ).run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()

    app = app.button(key="save_runtime_evidence").click().run()

    assert len(app.session_state["review_state"].bundle.runtime_evidence) == 1
    assert (
        app.session_state["review_state"].resolution_events[-1].decision
        is HumanDecision.MANUALLY_VERIFIED
    )
    assert app.text_input(key="runtime_artifact_reference").value == ""
    captions = "\n".join(item.value for item in app.caption)
    assert "Pending criterion-detail inputs are not saved or exported." not in captions
    assert "Saved locally — current review matches local storage." in captions
    assert app.button(key="save_review").disabled is True
    assert all(not button.disabled for button in app.download_button)
    assert JsonReviewStore(default_local_review_directory()).load(review_id) == (
        app.session_state["review_state"]
    )


def test_pending_criteria_edit_is_not_claimed_saved_or_exportable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    authoritative_state = app.session_state["review_state"].model_copy(deep=True)

    app = app.text_input(key="criterion_text_AC-01").set_value(
        "Pending revised export requirement"
    ).run()
    app = app.selectbox(key="criterion_priority_AC-01").set_value(
        Priority.SHOULD_HAVE
    ).run()
    app = app.selectbox(key="criterion_level_AC-01").set_value(
        EvidenceLevel.E3
    ).run()

    captions = "\n".join(item.value for item in app.caption)
    sidebar = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Saved locally — current review matches local storage." not in captions
    assert (
        "Pending criteria edits are not saved or exported. Confirm or discard them "
        "before relying on this review ID."
    ) in captions
    assert app.button(key="save_review").disabled is True
    assert app.button(key="load_demo").disabled is True
    assert app.checkbox(key="replace_unsaved_review_confirmed").value is False
    assert app.button(key="discard_criteria_draft").disabled is False
    assert "Pending — Resolve inputs before export" in sidebar
    _assert_pending_draft_preserves_authoritative_review(
        app,
        review_id=review_id,
        authoritative_state=authoritative_state,
    )


def test_discard_unconfirmed_criteria_edits_restores_saved_exportable_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, _ = saved_demo_review(new_app())
    review_state = app.session_state["review_state"].model_copy(deep=True)
    criterion = app.session_state["criteria"][0]
    app = app.text_input(key="criterion_text_AC-01").set_value(
        "Pending revised export requirement"
    ).run()
    app = app.selectbox(key="criterion_priority_AC-01").set_value(
        Priority.SHOULD_HAVE
    ).run()
    app = app.selectbox(key="criterion_level_AC-01").set_value(
        EvidenceLevel.E3
    ).run()

    app = app.button(key="discard_criteria_draft").click().run()

    assert app.session_state["review_state"] == review_state
    assert app.text_input(key="criterion_text_AC-01").value == criterion.text
    assert app.selectbox(key="criterion_priority_AC-01").value is criterion.priority
    assert (
        app.selectbox(key="criterion_level_AC-01").value
        is criterion.required_evidence_level
    )
    assert "Unconfirmed criteria edits discarded without changing the review." in [
        item.value for item in app.success
    ]
    captions = "\n".join(item.value for item in app.caption)
    sidebar = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Saved locally — current review matches local storage." in captions
    assert "Pending criteria edits are not saved or exported." not in captions
    assert app.button(key="save_review").disabled is True
    assert all(not button.disabled for button in app.download_button)
    assert app.button(key="load_demo").disabled is False
    assert "Available — Review evidence and export" in sidebar


@pytest.mark.parametrize(
    ("input_kind", "input_key", "input_value", "submit_key"),
    [
        (
            "text_input",
            "new_criterion_text",
            "Draft a new export behavior",
            "add_criterion_ui",
        ),
        (
            "text_area",
            "split_criterion_text",
            "Export CSV\nRecord analytics",
            "split_criterion_ui",
        ),
    ],
)
def test_pending_criteria_authoring_draft_is_not_claimed_saved_or_exportable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    input_kind: str,
    input_key: str,
    input_value: str,
    submit_key: str,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    authoritative_state = app.session_state["review_state"].model_copy(deep=True)

    widget = getattr(app, input_kind)(key=input_key)
    app = widget.set_value(input_value).run()

    captions = "\n".join(item.value for item in app.caption)
    sidebar = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Saved locally — current review matches local storage." not in captions
    assert (
        "Pending add or split criterion inputs are not saved or exported. Submit or "
        "clear them before relying on this review ID."
    ) in captions
    assert app.button(key="save_review").disabled is True
    assert app.button(key="load_demo").disabled is True
    assert app.checkbox(key="replace_unsaved_review_confirmed").value is False
    assert app.button(key="clear_criteria_authoring_drafts").disabled is False
    assert app.button(key=submit_key).disabled is False
    assert "Pending — Resolve inputs before export" in sidebar
    _assert_pending_draft_preserves_authoritative_review(
        app,
        review_id=review_id,
        authoritative_state=authoritative_state,
    )


def test_clear_criteria_authoring_drafts_restores_saved_exportable_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, _ = saved_demo_review(new_app())
    review_state = app.session_state["review_state"].model_copy(deep=True)
    app = app.text_input(key="new_criterion_text").set_value(
        "Draft a new export behavior"
    ).run()
    app = app.text_area(key="split_criterion_text").set_value(
        "Export CSV\nRecord analytics"
    ).run()

    app = app.button(key="clear_criteria_authoring_drafts").click().run()

    assert app.session_state["review_state"] == review_state
    assert app.text_input(key="new_criterion_text").value == ""
    assert app.text_area(key="split_criterion_text").value == ""
    assert "Unsubmitted add and split inputs cleared without changing the review." in [
        item.value for item in app.success
    ]
    captions = "\n".join(item.value for item in app.caption)
    sidebar = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Saved locally — current review matches local storage." in captions
    assert "Pending add or split criterion inputs are not saved or exported." not in captions
    assert app.button(key="save_review").disabled is True
    assert all(not button.disabled for button in app.download_button)
    assert app.button(key="load_demo").disabled is False
    assert "Available — Review evidence and export" in sidebar


@pytest.mark.parametrize(
    ("input_kind", "input_key", "input_value", "submit_key"),
    [
        (
            "text_input",
            "new_criterion_text",
            "Document export format",
            "add_criterion_ui",
        ),
        (
            "text_area",
            "split_criterion_text",
            "Export CSV\nRecord analytics",
            "split_criterion_ui",
        ),
    ],
)
def test_successful_criteria_authoring_action_clears_consumed_input(
    input_kind: str,
    input_key: str,
    input_value: str,
    submit_key: str,
) -> None:
    app = load_demo(new_app())
    app = getattr(app, input_kind)(key=input_key).set_value(input_value).run()

    app = app.button(key=submit_key).click().run()

    assert getattr(app, input_kind)(key=input_key).value == ""
    assert app.button(key=submit_key).disabled is True


def test_pending_requirements_draft_is_not_claimed_saved_or_exportable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    authoritative_state = app.session_state["review_state"].model_copy(deep=True)
    requirements_draft = (
        f"{app.session_state['source_text']}\nDraft requirement not yet prepared"
    )

    app = app.text_area(key="requirements_input").set_value(requirements_draft).run()

    captions = "\n".join(item.value for item in app.caption)
    sidebar = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Saved locally — current review matches local storage." not in captions
    assert (
        "Pending requirements changes are not saved or exported. Prepare or discard "
        "them before relying on this review ID."
    ) in captions
    assert app.button(key="save_review").disabled is True
    assert app.button(key="load_demo").disabled is True
    assert app.checkbox(key="replace_unsaved_review_confirmed").value is False
    assert app.button(key="discard_requirements_draft").disabled is False
    assert app.button(key="prepare_criteria").disabled is False
    assert "Pending — Resolve inputs before export" in sidebar
    _assert_pending_draft_preserves_authoritative_review(
        app,
        review_id=review_id,
        authoritative_state=authoritative_state,
    )

    app = app.text_input(key="new_criterion_text").set_value(
        "Unrelated criterion edit"
    ).run()
    assert app.button(key="add_criterion_ui").disabled is True


def test_discard_requirements_draft_restores_authoritative_saved_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, _ = saved_demo_review(new_app())
    review_state = app.session_state["review_state"].model_copy(deep=True)
    authoritative_source = app.session_state["source_text"]
    app = app.text_area(key="requirements_input").set_value(
        f"{authoritative_source}\nDraft requirement not yet prepared"
    ).run()

    app = app.button(key="discard_requirements_draft").click().run()

    assert app.session_state["review_state"] == review_state
    assert app.session_state["source_text"] == authoritative_source
    assert app.text_area(key="requirements_input").value == authoritative_source
    assert "Unprepared requirements changes discarded without changing the review." in [
        item.value for item in app.success
    ]
    captions = "\n".join(item.value for item in app.caption)
    sidebar = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Saved locally — current review matches local storage." in captions
    assert "Pending requirements changes are not saved or exported." not in captions
    assert app.button(key="save_review").disabled is True
    assert all(not button.disabled for button in app.download_button)
    assert app.button(key="load_demo").disabled is False
    assert "Available — Review evidence and export" in sidebar


def test_prepare_criteria_consumes_pending_requirements_draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, _ = saved_demo_review(new_app())
    requirements_draft = "Export PDF\nRecord the export event"
    app = app.text_area(key="requirements_input").set_value(requirements_draft).run()

    assert app.button(key="prepare_criteria").disabled is False
    app = app.button(key="prepare_criteria").click().run()

    assert app.session_state["review_state"] is None
    assert app.session_state["source_text"] == requirements_draft
    assert app.text_area(key="requirements_input").value == requirements_draft
    assert [item.text for item in app.session_state["criteria"]] == [
        "Export PDF",
        "Record the export event",
    ]
    assert not [
        item for item in app.checkbox if item.key == "replace_unsaved_review_confirmed"
    ]


def test_confirmed_criteria_edit_with_no_bundle_autosaves_authoritative_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    app = app.text_input(key="criterion_text_AC-01").set_value(
        "Confirmed revised export requirement"
    ).run()

    app = app.button(key="confirm_criteria").click().run()

    review_state = app.session_state["review_state"]
    assert review_state.criteria_revision.number == 2
    assert review_state.criteria_revision.criteria[0].text == (
        "Confirmed revised export requirement"
    )
    assert review_state.bundle is None
    assert JsonReviewStore(default_local_review_directory()).load(
        review_id
    ) == review_state
    assert app.session_state["saved_review_fingerprint"] == (
        _review_fingerprint_for_test(review_state)
    )
    assert app.session_state["criteria_confirmed"] is True
    assert app.button(key="confirm_criteria").disabled is True
    assert app.button(key="run_analysis").disabled is False
    assert "Criteria edits are pending confirmation." not in "\n".join(
        item.value for item in app.warning
    )


def test_bundleless_revision_can_clear_criterion_draft_and_resume_autosave(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value(
        "pending-runtime-artifact"
    ).run()
    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.ACCEPTED
    ).run()
    app.session_state["manual_evidence_level"] = EvidenceLevel.E4
    app = app.text_input(key="criterion_text_AC-01").set_value(
        "Confirmed revised export requirement with pending detail"
    ).run()

    app = app.button(key="confirm_criteria").click().run()

    authoritative_state = app.session_state["review_state"].model_copy(deep=True)
    assert authoritative_state.bundle is None
    clear_actions = [
        button
        for button in app.button
        if button.key == "clear_criterion_detail_drafts"
    ]
    warning = (
        "Pending criterion inputs are not part of the review, local save, or exports. "
        "Clear them to continue with this revised review."
    )
    assert app.session_state["manual_evidence_level"] is EvidenceLevel.E4
    assert JsonReviewStore(default_local_review_directory()).load(
        review_id
    ) != authoritative_state
    assert not app.download_button
    assert warning in [item.value for item in app.warning]
    assert len(clear_actions) == 1
    assert clear_actions[0].disabled is False

    app = app.button(key="clear_criterion_detail_drafts").click().run()

    assert app.session_state["review_state"] == authoritative_state
    assert app.session_state["runtime_artifact_reference"] == ""
    assert app.session_state["runtime_evidence_level"] is EvidenceLevel.E3
    assert app.session_state["resolution_decision"] is None
    assert app.session_state["resolution_note"] == ""
    assert "manual_evidence_level" not in app.session_state
    assert "Pending criterion inputs cleared without changing the review." in [
        item.value for item in app.success
    ]
    assert JsonReviewStore(default_local_review_directory()).load(
        review_id
    ) == authoritative_state
    assert app.session_state["saved_review_fingerprint"] == (
        _review_fingerprint_for_test(authoritative_state)
    )
    assert not app.download_button

    app = app.button(key="run_analysis").click().run()

    assert app.session_state["review_state"].bundle is not None
    assert all(not button.disabled for button in app.download_button)


def test_reopened_bundleless_failed_autosave_exposes_expanded_retry_and_persists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())
    app = select_saved_review(new_app(), review_id)
    app = app.button(key="reopen_review").click().run()
    app = app.text_input(key="criterion_text_AC-01").set_value(
        "Confirmed bundleless requirement after save failure"
    ).run()

    with patch(
        "scopeproof_core.storage.json_store.JsonReviewStore.save",
        side_effect=OSError("disk full at /private/secret/path"),
    ) as save:
        app = app.button(key="confirm_criteria").click().run()
        assert save.call_count == 1
        app = app.run()
        assert save.call_count == 1

    state = app.session_state["review_state"]
    assert state.bundle is None
    assert app.session_state["failed_review_save_fingerprint"] == (
        _review_fingerprint_for_test(state)
    )
    local_storage = next(
        item for item in app.expander if item.label == "Local review storage"
    )
    assert local_storage.proto.expanded is True
    assert app.button(key="save_review").label == "Retry local save"
    assert app.button(key="save_review").disabled is False

    app = app.button(key="save_review").click().run()

    assert JsonReviewStore(default_local_review_directory()).load(review_id) == state
    assert app.session_state["saved_review_fingerprint"] == (
        _review_fingerprint_for_test(state)
    )
    assert app.session_state["failed_review_save_fingerprint"] is None


def test_bundleless_deleted_review_exposes_save_now_and_recreates_on_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    app = app.text_input(key="criterion_text_AC-01").set_value(
        "Confirmed bundleless requirement before deletion"
    ).run()
    app = app.button(key="confirm_criteria").click().run()
    state = app.session_state["review_state"]
    assert state.bundle is None
    app = select_saved_review(app, review_id)
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()

    app = app.button(key="delete_saved_review").click().run()
    app = app.run()

    with pytest.raises(FileNotFoundError):
        JsonReviewStore(default_local_review_directory()).load(review_id)
    assert app.session_state["deleted_review_save_fingerprint"] == (
        _review_fingerprint_for_test(state)
    )
    assert app.button(key="save_review").label == "Save now"
    assert app.button(key="save_review").disabled is False

    app = app.button(key="save_review").click().run()

    assert JsonReviewStore(default_local_review_directory()).load(review_id) == state
    assert app.session_state["saved_review_fingerprint"] == (
        _review_fingerprint_for_test(state)
    )
    assert app.session_state["deleted_review_save_fingerprint"] is None


@pytest.mark.parametrize(
    "save_error",
    [OSError("disk full at /private/secret/path"), ValueError("invalid state")],
)
def test_autosave_failure_attempts_once_and_preserves_explicit_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    save_error: OSError | ValueError,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    with patch(
        "scopeproof_core.storage.json_store.JsonReviewStore.save",
        side_effect=save_error,
    ) as save:
        app = app.button(key="run_analysis").click().run()
        assert save.call_count == 1
        app = app.run()
        assert save.call_count == 1

    state = app.session_state["review_state"]
    assert app.session_state["saved_review_fingerprint"] is None
    assert app.session_state["failed_review_save_fingerprint"] == (
        _review_fingerprint_for_test(state)
    )
    assert app.button(key="save_review").label == "Retry local save"
    assert app.button(key="save_review").disabled is False
    assert all(not button.disabled for button in app.download_button)
    assert "/private/secret/path" not in "\n".join(
        item.value for item in [*app.error, *app.warning, *app.caption]
    )


def test_explicit_retry_after_autosave_failure_persists_and_clears_markers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    with patch(
        "scopeproof_core.storage.json_store.JsonReviewStore.save",
        side_effect=OSError("disk full"),
    ):
        app = app.button(key="run_analysis").click().run()

    state = app.session_state["review_state"]
    app = app.button(key="save_review").click().run()

    assert JsonReviewStore(default_local_review_directory()).load(
        state.review.review_id
    ) == state
    assert app.session_state["saved_review_fingerprint"] == (
        _review_fingerprint_for_test(state)
    )
    assert app.session_state["failed_review_save_fingerprint"] is None
    assert app.session_state["deleted_review_save_fingerprint"] is None


def test_post_save_resolution_changes_fingerprint_and_autosaves_review_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    previous_state = app.session_state["review_state"]
    previous_fingerprint = _review_fingerprint_for_test(previous_state)
    assert app.button(key="save_review").disabled is True

    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.ACCEPTED
    ).run()
    app = app.button(key="save_resolution").click().run()

    persisted_state = JsonReviewStore(default_local_review_directory()).load(review_id)
    current_state = app.session_state["review_state"]
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Saved locally — current review matches local storage." in caption_text
    assert _review_fingerprint_for_test(current_state) != previous_fingerprint
    assert persisted_state == current_state
    assert app.button(key="save_review").disabled is True


def test_pending_resolution_input_does_not_overwrite_external_lifecycle_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    store = JsonReviewStore(default_local_review_directory())
    external, _ = store.mutate(
        review_id,
        lambda state: append_resolution(
            state,
            ResolutionEvent(
                event_id="external-cli-revocation",
                final_acceptance=False,
                comment="CLI revocation while workbench remained open",
                reviewer="CLI reviewer",
            ),
        ),
    )

    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.ACCEPTED
    ).run()
    app = app.button(key="save_resolution").click().run()

    assert store.load(review_id) == external
    assert app.session_state["review_state"] != external
    messages = [item.value for item in [*app.error, *app.warning]]
    assert any("changed outside this workbench" in message for message in messages)
    assert any(
        "newer lifecycle events are not overwritten" in message
        for message in messages
    )


def test_clean_open_workbench_refreshes_external_final_acceptance_revocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = resolve_all_criteria(analyzed_demo(new_app()))
    app = app.button(key="record_final_acceptance").click().run()
    accepted = app.session_state["review_state"]
    assert accepted.bundle.gate.verdict is GateVerdict.READY
    review_id = accepted.review.review_id
    store = JsonReviewStore(default_local_review_directory())
    revoked, _ = store.mutate(
        review_id,
        lambda state: append_resolution(
            state,
            ResolutionEvent(
                event_id="external-cli-final-revocation",
                final_acceptance=False,
                comment="CLI revocation while accepted review remained open",
                reviewer="CLI reviewer",
            ),
        ),
    )

    app = app.run()

    assert app.session_state["review_state"] == revoked
    assert app.session_state["bundle"] == revoked.bundle
    assert app.session_state["saved_review_fingerprint"] == (
        _review_fingerprint_for_test(revoked)
    )
    assert revoked.bundle.gate.verdict is not GateVerdict.READY
    assert "**Review status: Review complete**" not in [
        item.value for item in app.markdown
    ]
    assert "Review refreshed from local storage after an external update." in [
        item.value for item in app.success
    ]
    assert all(button.proto.deferred_file_id for button in app.download_button)
    assert all(not button.proto.url for button in app.download_button)


def test_clean_open_workbench_refresh_and_status_use_shared_record_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = resolve_all_criteria(analyzed_demo(new_app()))
    app = app.button(key="record_final_acceptance").click().run()
    review_id = app.session_state["review_state"].review.review_id
    locked_review_ids: list[str] = []
    original_locked_load = JsonReviewStore.locked_load

    @contextmanager
    def tracking_locked_load(store: JsonReviewStore, target_review_id: str):
        locked_review_ids.append(target_review_id)
        with original_locked_load(store, target_review_id) as state:
            yield state

    with patch.object(JsonReviewStore, "locked_load", tracking_locked_load):
        app = app.run()

    assert not app.exception
    assert locked_review_ids == [review_id, review_id]


def test_failed_persisted_review_revalidation_blocks_status_and_exports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = resolve_all_criteria(analyzed_demo(new_app()))
    app = app.button(key="record_final_acceptance").click().run()

    with patch(
        "scopeproof_core.storage.json_store.JsonReviewStore.load",
        side_effect=OSError("synthetic local read failure"),
    ):
        app = app.run()

    assert "**Review status: Refresh required**" in [
        item.value for item in app.markdown
    ]
    assert all(button.disabled for button in app.download_button)
    assert any(
        "could not be revalidated" in item.value for item in app.warning
    )
    assert "synthetic local read failure" not in "\n".join(
        item.value for item in [*app.warning, *app.error]
    )


def test_unavailable_saved_review_store_blocks_status_and_exports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = resolve_all_criteria(analyzed_demo(new_app()))
    app = app.button(key="record_final_acceptance").click().run()

    with patch(
        "scopeproof_core.storage.json_store.JsonReviewStore.list_review_ids",
        side_effect=OSError("synthetic unavailable review store"),
    ):
        app = app.run()

    assert app.session_state["saved_review_fingerprint"] is None
    assert app.session_state["review_save_conflict"] is True
    assert "**Review status: Refresh required**" in [
        item.value for item in app.markdown
    ]
    assert all(button.disabled for button in app.download_button)
    assert "synthetic unavailable review store" not in "\n".join(
        item.value for item in [*app.warning, *app.error]
    )


def test_external_update_preserves_pending_input_and_blocks_stale_exports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = resolve_all_criteria(analyzed_demo(new_app()))
    app = app.button(key="record_final_acceptance").click().run()
    accepted = app.session_state["review_state"]
    app = app.text_input(key="runtime_artifact_reference").set_value(
        "pending-runtime-artifact"
    ).run()
    JsonReviewStore(default_local_review_directory()).mutate(
        accepted.review.review_id,
        lambda state: append_resolution(
            state,
            ResolutionEvent(
                event_id="external-revocation-with-pending-input",
                final_acceptance=False,
                comment="External revocation while workbench input was pending",
                reviewer="CLI reviewer",
            ),
        ),
    )

    app = app.run()

    assert app.session_state["review_state"] == accepted
    assert app.text_input(key="runtime_artifact_reference").value == (
        "pending-runtime-artifact"
    )
    assert "**Review status: Refresh required**" in [
        item.value for item in app.markdown
    ]
    assert all(button.disabled for button in app.download_button)
    assert any(
        "changed outside this workbench" in item.value for item in app.warning
    )


def test_unsaved_review_requires_explicit_approval_before_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, saved_review_id = saved_demo_review(new_app())
    app = analyzed_demo(new_app())
    app = select_saved_review(app, saved_review_id)
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/example/pull/7"
    ).run()
    app = app.text_input(key="new_criterion_text").set_value("A new behavior").run()
    app = app.text_area(key="split_criterion_text").set_value(
        "First behavior\nSecond behavior"
    ).run()

    warning_text = "\n".join(item.value for item in app.warning)
    assert "Replacing it will discard unsaved changes." in warning_text
    assert app.checkbox(key="replace_unsaved_review_confirmed").value is False
    assert app.button(key="reopen_review").disabled is True
    assert app.button(key="load_demo").disabled is True
    assert app.button(key="fetch_pr").disabled is True
    assert app.button(key="prepare_criteria").disabled is True
    assert app.button(key="add_criterion_ui").disabled is False
    assert app.button(key="split_criterion_ui").disabled is False
    assert all(
        button.disabled
        for button in app.button
        if button.key.startswith(("remove_", "move_up_"))
    )

    app = app.checkbox(key="replace_unsaved_review_confirmed").check().run()

    assert app.button(key="reopen_review").disabled is False
    assert app.button(key="load_demo").disabled is False
    assert app.button(key="fetch_pr").disabled is False
    assert app.button(key="prepare_criteria").disabled is False
    assert app.button(key="add_criterion_ui").disabled is False
    assert app.button(key="split_criterion_ui").disabled is False
    assert all(
        not button.disabled
        for button in app.button
        if button.key.startswith(("remove_", "move_up_"))
    )


def test_replacing_unsaved_review_consumes_replacement_approval() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="new_criterion_text").set_value(
        "Pending criterion before replacement"
    ).run()
    app = app.checkbox(key="replace_unsaved_review_confirmed").check().run()
    app = app.button(key="load_demo").click().run()

    assert app.session_state["review_state"] is None
    assert app.session_state["replace_unsaved_review_confirmed"] is False
    assert not [
        item
        for item in app.checkbox
        if item.key == "replace_unsaved_review_confirmed"
    ]


def test_saved_review_can_be_reopened_from_a_fresh_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_state = saved.session_state["review_state"]

    fresh = new_app()
    assert fresh.selectbox(key="saved_reopen_review_id").value is None
    fresh = select_saved_review(fresh, review_id)
    fresh = fresh.button(key="reopen_review").click().run()

    reopened = fresh.session_state["review_state"]
    assert reopened == saved_state
    assert fresh.session_state["bundle"] == saved_state.bundle
    assert fresh.session_state["criteria"] == saved_state.criteria_revision.criteria
    assert fresh.session_state["criteria_confirmed"] is True
    assert fresh.session_state["source_text"] == saved_state.criteria_revision.source_text
    assert (
        fresh.text_area(key="requirements_input").value
        == saved_state.criteria_revision.source_text
    )
    assert fresh.session_state["snapshot"] is None
    assert fresh.button(key="run_analysis").disabled is True
    assert len(fresh.download_button) == 3
    assert review_id in [item.value for item in fresh.code]
    caption_text = "\n".join(item.value for item in fresh.caption)
    assert "Saved locally — current review matches local storage." in caption_text
    assert fresh.button(key="save_review").disabled is True


def test_reopened_review_prepares_one_click_current_head_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    state = saved.session_state["review_state"]

    fresh = select_saved_review(new_app(), review_id)
    fresh = fresh.button(key="reopen_review").click().run()

    assert fresh.text_input(key="pr_url").value == (
        f"https://github.com/{state.review.repository}/pull/{state.review.pr_number}"
    )
    assert fresh.text_area(key="candidate_paths").value == ""
    assert fresh.button(key="fetch_pr").label == "Check current head"


def test_reopened_review_restores_unique_unchanged_candidate_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    state = saved.session_state["review_state"].model_copy(deep=True)
    assert state.bundle is not None
    state.bundle.evidence[0].source_scope = EvidenceSourceScope.UNCHANGED_CANDIDATE
    state.bundle.evidence[0].file_path = "src/unchanged.py"
    state.bundle.evidence[1].source_scope = EvidenceSourceScope.UNCHANGED_CANDIDATE
    state.bundle.evidence[1].file_path = "src/unchanged.py"
    state = ReviewState.model_validate(state.model_dump(mode="python"))
    JsonReviewStore(default_local_review_directory()).save(state)

    fresh = select_saved_review(new_app(), review_id)
    fresh = fresh.button(key="reopen_review").click().run()

    assert fresh.text_area(key="candidate_paths").value == "src/unchanged.py"
    assert fresh.button(key="fetch_pr").label == "Check current head"


def test_reopening_clears_an_unrelated_loaded_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())

    app = load_demo(new_app())
    assert app.session_state["snapshot"] is not None
    app = select_saved_review(app, review_id)
    app = app.button(key="reopen_review").click().run()

    assert app.session_state["snapshot"] is None
    assert app.button(key="run_analysis").disabled is True
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Next — Reload source to rerun analysis" in sidebar_text


def test_reopened_review_reports_changed_head_before_invalidating_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_head = saved.session_state["review_state"].review.head_sha
    changed_head = "changed-head-for-regression"
    changed_snapshot = load_demo_snapshot().model_copy(update={"head_sha": changed_head})

    fresh = new_app()
    fresh = select_saved_review(fresh, review_id)
    fresh = fresh.button(key="reopen_review").click().run()
    with patch("scopeproof_core.demo.load_demo_snapshot", return_value=changed_snapshot):
        fresh = fresh.button(key="load_demo").click().run()

    warning_text = "\n".join(item.value for item in fresh.warning)
    assert saved_head in warning_text
    assert changed_head in warning_text
    assert "saved evidence remains anchored" in warning_text
    assert fresh.session_state["review_state"] is None
    assert fresh.session_state["bundle"] is None
    assert fresh.session_state["criteria_confirmed"] is False
    assert fresh.button(key="run_analysis").disabled is True


def test_reanalysis_shows_previous_and_current_head_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved = analyzed_exact_head_standard_demo(new_app())
    review_id = saved.session_state["review_state"].review.review_id
    previous_head = saved.session_state["review_state"].review.head_sha
    changed_snapshot = load_demo_snapshot().model_copy(
        update={
            "head_sha": "b" * 40,
            "repository_visibility": RepositoryVisibility.VERIFIED_PUBLIC,
        }
    )

    fresh = new_app()
    fresh = select_saved_review(fresh, review_id)
    fresh = fresh.button(key="reopen_review").click().run()
    fresh = fresh.text_input(key="pr_url").set_value(
        "https://github.com/scopeproof/demo-stock-research/pull/7"
    ).run()
    with patch(
        "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
        return_value=changed_snapshot,
    ):
        fresh = fresh.button(key="fetch_pr").click().run()
    fresh = fresh.text_input(key="criteria_source_reference").set_value(
        "https://github.com/acme/repo/issues/6"
    ).run()
    fresh = fresh.text_input(key="criteria_source_confirmer").set_value(
        "Local reviewer"
    ).run()
    fresh = fresh.button(key="confirm_criteria").click().run()
    fresh = fresh.button(key="run_analysis").click().run()

    rendered = "\n".join(
        item.value for item in [*fresh.markdown, *fresh.caption, *fresh.code]
    )
    assert f"Previous head: {previous_head}" in rendered
    assert f"Current head: {changed_snapshot.head_sha}" in rendered
    assert "Relocated: 9" in rendered
    assert "Previous candidate" in rendered
    assert "Current candidate" in rendered
    assert "review the current evidence" in rendered.lower()
    assert "does not prove criterion satisfaction" in rendered.lower()


def test_same_head_reanalysis_exposes_unchanged_candidates_and_comparison_exports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_state = saved.session_state["review_state"]
    assert saved_state.bundle is not None
    expected_permalinks = {item.permalink for item in saved_state.bundle.evidence}

    fresh = select_saved_review(new_app(), review_id)
    fresh = fresh.button(key="reopen_review").click().run()
    fresh = fresh.button(key="load_demo").click().run()
    fresh = fresh.text_input(key="criteria_source_confirmer").set_value(
        "Local reviewer"
    ).run()
    fresh = fresh.button(key="confirm_criteria").click().run()
    fresh = fresh.button(key="run_analysis").click().run()

    unchanged = next(
        item for item in fresh.expander if item.label.startswith("Unchanged candidates (")
    )
    assert unchanged.proto.expanded is False
    unchanged_markdown = [item.value for item in unchanged.markdown]
    assert "**Previous candidate**" in unchanged_markdown
    assert "**Current candidate**" in unchanged_markdown
    for permalink in expected_permalinks:
        assert any(f"](<{permalink}>)" in item for item in unchanged_markdown)
    comparison_downloads = {
        button.key: button for button in fresh.download_button
        if button.key.startswith("download_comparison_")
    }
    assert set(comparison_downloads) == {
        "download_comparison_markdown",
        "download_comparison_json",
    }
    assert all(not button.disabled for button in comparison_downloads.values())


def test_comparison_view_shows_removed_external_junit_import_as_non_gating() -> None:
    app = analyzed_exact_head_standard_demo(new_app())
    current_state = app.session_state["review_state"]
    criterion_id = current_state.criteria_revision.criteria[0].criterion_id
    current_state = append_resolution(
        current_state,
        ResolutionEvent(
            criterion_id=criterion_id,
            decision=HumanDecision.ACCEPTED,
            comment="Reviewed before the imported context changed.",
        ),
    )
    imported = build_junit_evidence_import(
        current_state,
        b'<testsuite name="unit"><testcase name="test_export"/></testsuite>',
        [
            JUnitMappingSelection(
                scope_id="suite-0001",
                criterion_id=criterion_id,
            )
        ],
        importer="QA owner",
        import_id="junit-comparison-import",
    )
    previous_state = append_junit_evidence_import(current_state, imported)
    assert previous_state.bundle is not None
    app.session_state["comparison_base_bundle"] = previous_state.bundle
    app.session_state["review_state"] = current_state
    app.session_state["bundle"] = current_state.bundle

    app = app.run()

    assert app.exception == []
    rendered = "\n".join(
        item.value for item in [*app.markdown, *app.caption, *app.text, *app.code]
    )
    assert "Imported external test result changes" in rendered
    assert "Removed" in rendered
    assert imported.artifact_sha256 in rendered
    assert "externally supplied, non-gating context" in rendered.lower()
    assert "did not execute" in rendered.lower()
    assert "imported bytes only" in rendered.lower()
    assert "asserted, not authenticated" in rendered.lower()
    assert "organizational context, not proof" in rendered.lower()
    warnings = "\n".join(item.value for item in app.warning)
    assert "does not carry a prior decision forward automatically" in warnings
    assert "changed head" not in warnings


def test_ineligible_comparison_base_is_cleared_without_hiding_current_analysis() -> None:
    app = analyzed_demo(new_app())
    current_bundle = app.session_state["bundle"].model_copy(deep=True)
    comparison_base = current_bundle.model_copy(deep=True)
    provenance = comparison_base.review.criteria_source_provenance
    assert provenance is not None
    comparison_base.review = comparison_base.review.model_copy(
        update={
            "criteria_source_provenance": provenance.model_copy(
                update={"source_uri": "https://example.test/stale-criteria-source"}
            )
        }
    )
    app.session_state["comparison_base_bundle"] = comparison_base

    app = app.run()

    assert app.session_state["comparison_base_bundle"] is None
    assert app.session_state["bundle"] == current_bundle
    assert any(
        "previous review cannot be compared" in item.value.lower()
        and "no prior decisions were carried forward" in item.value.lower()
        for item in app.warning
    )
    assert not [
        button
        for button in app.download_button
        if button.key.startswith("download_comparison_")
    ]
    rendered = "\n".join(item.value for item in [*app.markdown, *app.caption])
    assert "Evidence status describes deterministic candidates" in rendered


def test_comparison_renders_removed_prior_decision_without_carrying_it_forward() -> None:
    app = analyzed_demo(new_app())
    current_state = app.session_state["review_state"]
    current_bundle = current_state.bundle.model_copy(deep=True)
    previous_state = append_resolution(
        current_state,
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            comment="Previous reviewer decision",
        ),
    )
    assert previous_state.bundle is not None
    app.session_state["comparison_base_bundle"] = previous_state.bundle
    app.session_state["review_state"] = current_state
    app.session_state["bundle"] = current_bundle

    app = app.run()

    rendered = "\n".join(item.value for item in app.markdown)
    assert "Changed reviewer decisions" in rendered
    assert "AC-01: Accepted → None" in rendered
    assert app.session_state["review_state"] == current_state
    assert current_bundle.resolutions == []


def test_comparison_renders_changed_finding_status_from_current_evidence_only() -> None:
    app = analyzed_demo(new_app())
    current_state = app.session_state["review_state"]
    assert current_state.bundle is not None
    comparison_base = current_state.bundle.model_copy(deep=True)
    current_bundle = current_state.bundle.model_copy(deep=True)
    current_bundle.evidence = [
        item for item in current_bundle.evidence if item.criterion_id != "AC-01"
    ]
    current_bundle.retrieval_diagnostics = []
    current_bundle.findings = build_findings(
        current_bundle.criteria,
        current_bundle.evidence,
        current_bundle.review.ingestion_state,
    )
    current_bundle.gate = evaluate_gate(
        current_bundle.review,
        current_bundle.criteria,
        current_bundle.findings,
        current_bundle.resolutions,
    )
    current_state = ReviewState.model_validate(
        current_state.model_copy(update={"bundle": current_bundle}).model_dump(
            mode="python"
        )
    )
    app.session_state["comparison_base_bundle"] = comparison_base
    app.session_state["review_state"] = current_state
    app.session_state["bundle"] = current_bundle

    app = app.run()

    rendered = "\n".join(item.value for item in app.markdown)
    assert "Changed criterion findings" in rendered
    assert "AC-01: Evidence Found → Missing" in rendered
    assert app.session_state["bundle"] == current_bundle


def test_rereview_comparison_shows_modified_candidate_excerpt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved = analyzed_exact_head_standard_demo(new_app())
    review_id = saved.session_state["review_state"].review.review_id
    original = load_demo_snapshot()
    files = [item.model_copy(deep=True) for item in original.files]
    lines = [item.model_copy(deep=True) for item in files[0].lines]
    lines[0] = lines[0].model_copy(
        update={
            "content": "def export_research_list_csv_safe(rows, active_sector=None):"
        }
    )
    files[0] = files[0].model_copy(update={"lines": lines})
    changed_snapshot = original.model_copy(
        update={
            "head_sha": "c" * 40,
            "repository_visibility": RepositoryVisibility.VERIFIED_PUBLIC,
            "files": files,
        }
    )

    fresh = new_app()
    fresh = select_saved_review(fresh, review_id)
    fresh = fresh.button(key="reopen_review").click().run()
    fresh = fresh.text_input(key="pr_url").set_value(
        "https://github.com/scopeproof/demo-stock-research/pull/7"
    ).run()
    with patch(
        "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
        return_value=changed_snapshot,
    ):
        fresh = fresh.button(key="fetch_pr").click().run()
    fresh = fresh.text_input(key="criteria_source_reference").set_value(
        "https://github.com/acme/repo/issues/6"
    ).run()
    fresh = fresh.text_input(key="criteria_source_confirmer").set_value(
        "Local reviewer"
    ).run()
    fresh = fresh.button(key="confirm_criteria").click().run()
    fresh = fresh.button(key="run_analysis").click().run()

    rendered = "\n".join(
        item.value for item in [*fresh.markdown, *fresh.caption, *fresh.code]
    )
    assert "Modified" in rendered
    assert "def export_research_list_csv(rows, active_sector=None):" in rendered
    assert "def export_research_list_csv_safe(rows, active_sector=None):" in rendered
    assert "review the current evidence" in rendered.lower()


def test_reopened_review_reports_same_head_before_reanalysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_head = saved.session_state["review_state"].review.head_sha

    fresh = new_app()
    fresh = select_saved_review(fresh, review_id)
    fresh = fresh.button(key="reopen_review").click().run()
    fresh = fresh.button(key="load_demo").click().run()

    info_text = "\n".join(item.value for item in fresh.info)
    assert f"same head SHA: {saved_head}" in info_text
    assert fresh.session_state["review_state"] is None
    assert fresh.session_state["criteria_confirmed"] is False
    assert fresh.button(key="run_analysis").disabled is True


def test_reopened_review_does_not_compare_a_different_pull_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())
    unrelated_snapshot = load_demo_snapshot().model_copy(update={"pr_number": 999})

    fresh = new_app()
    fresh = select_saved_review(fresh, review_id)
    fresh = fresh.button(key="reopen_review").click().run()
    with patch("scopeproof_core.demo.load_demo_snapshot", return_value=unrelated_snapshot):
        fresh = fresh.button(key="load_demo").click().run()

    assert fresh.session_state.filtered_state.get("source_reload_notice", "missing") is None
    assert not any("PR head changed" in item.value for item in fresh.warning)


def test_missing_saved_review_has_safe_recovery_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = new_app()
    app = app.text_input(key="reopen_review_id").set_value("missing-review").run()
    app = app.button(key="reopen_review").click().run()

    assert [item.value for item in app.error] == [
        "No saved review was found for that review ID."
    ]
    assert app.session_state["review_state"] is None
    assert app.session_state["bundle"] is None


def test_final_acceptance_control_is_visible_only_after_analysis() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    assert app.button(key="record_final_acceptance").disabled is True
    assert (
        "Resolve every active criterion before recording final acceptance."
        in [item.value for item in app.caption]
    )


def test_final_acceptance_requires_resolutions_and_then_completes_gate() -> None:
    app = resolve_all_criteria(analyzed_demo(new_app()))
    state_before = app.session_state["review_state"]
    gate_before = state_before.bundle.gate

    markdown_text = "\n".join(item.value for item in app.markdown)
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Final review acceptance" in markdown_text
    assert "records a review-level acceptance event" in caption_text
    assert "does not resolve individual criteria or override the deterministic gate" in caption_text
    assert "Review every criterion and its evidence before recording" in caption_text

    app = app.button(key="record_final_acceptance").click().run()
    state_after = app.session_state["review_state"]

    assert state_after.review.final_acceptance is True
    assert state_after.bundle.gate.verdict is GateVerdict.READY
    assert state_after.bundle.gate.blocking_criteria == gate_before.blocking_criteria
    assert state_after.bundle.gate.unresolved_criteria == gate_before.unresolved_criteria
    assert len(state_after.resolution_events) == len(state_after.bundle.criteria) + 1
    assert app.button(key="record_final_acceptance").disabled is True
    assert "Final acceptance appended to the local review history." in [
        item.value for item in app.success
    ]
    assert "Current · revision 1" in [item.value for item in app.text]
    assert "Final acceptance" in [item.value for item in app.code]
    assert "Recorded" in [item.value for item in app.text]
    assert "Reviewer recorded final acceptance" in [item.value for item in app.text]


def test_pending_contradictory_resolution_blocks_final_acceptance_without_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = resolve_all_criteria(analyzed_demo(new_app()))
    authoritative_state = app.session_state["review_state"].model_copy(deep=True)
    review_id = authoritative_state.review.review_id
    assert app.button(key="record_final_acceptance").disabled is False

    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.CHANGE_REQUIRED
    ).run()

    assert app.button(key="record_final_acceptance").disabled is True
    app = app.button(key="record_final_acceptance").click().run()
    assert app.session_state["review_state"] == authoritative_state
    assert not any(
        event.final_acceptance
        for event in app.session_state["review_state"].resolution_events
    )

    app = app.button(key="clear_criterion_detail_drafts").click().run()

    assert app.session_state["review_state"] == authoritative_state
    assert JsonReviewStore(default_local_review_directory()).load(
        review_id
    ) == authoritative_state
    assert app.selectbox(key="resolution_decision").value is None
    assert app.button(key="record_final_acceptance").disabled is False


def test_final_acceptance_failure_preserves_retryable_state_without_raw_details() -> None:
    app = resolve_all_criteria(analyzed_demo(new_app()))
    review_state = app.session_state["review_state"].model_copy(deep=True)
    raw_error = "invalid final event at /private/secret/final.json"

    with patch(
        "scopeproof_core.reviews.lifecycle.append_resolution",
        side_effect=ValueError(raw_error),
    ):
        app = app.button(key="record_final_acceptance").click().run()

    recovery = (
        "Final acceptance could not be recorded. The review remains unchanged. Verify the "
        "active review state and try again."
    )
    assert recovery in [item.value for item in app.error]
    assert not app.exception
    rendered = "\n".join(
        item.value
        for item in [
            *app.error,
            *app.warning,
            *app.info,
            *app.success,
            *app.caption,
            *app.markdown,
            *app.code,
        ]
    )
    assert raw_error not in rendered
    assert "/private/secret/final.json" not in rendered
    assert app.session_state["review_state"] == review_state
    assert app.session_state["bundle"] == review_state.bundle
    assert app.session_state["saved_review_fingerprint"] == (
        _review_fingerprint_for_test(review_state)
    )
    assert len(app.session_state["review_state"].resolution_events) == len(
        review_state.bundle.criteria
    )
    assert app.button(key="record_final_acceptance").disabled is False
    assert "Final acceptance appended" not in "\n".join(
        item.value for item in app.success
    )


def test_criteria_revision_reenables_final_acceptance_after_invalidation() -> None:
    app = resolve_all_criteria(analyzed_demo(new_app()))
    app = app.button(key="record_final_acceptance").click().run()
    assert app.button(key="record_final_acceptance").disabled is True

    app = app.text_input(key="criterion_text_AC-01").set_value(
        "User can export the research list as a downloadable CSV"
    ).run()

    app = app.button(key="confirm_criteria").click().run()
    assert app.session_state["review_state"].review.final_acceptance is False
    assert app.session_state["review_state"].bundle is None
    app = app.button(key="run_analysis").click().run()
    assert app.button(key="record_final_acceptance").disabled is True


def test_analysis_is_disabled_with_active_bundle_and_enabled_for_pending_revision() -> None:
    app = analyzed_demo(new_app())

    assert app.button(key="run_analysis").disabled is True

    app = app.text_input(key="criterion_text_AC-01").set_value(
        "User can export the revised research list as a downloadable CSV"
    ).run()
    app = app.button(key="confirm_criteria").click().run()

    assert app.session_state["review_state"].bundle is None
    assert app.button(key="run_analysis").disabled is False


def test_reanalysis_preserves_review_lineage_and_prior_events() -> None:
    app = analyzed_demo(new_app())
    original_review_id = app.session_state["review_state"].review.review_id
    app = resolve_all_criteria(app)
    app = app.button(key="record_final_acceptance").click().run()
    original_bundle = app.session_state["review_state"].bundle.model_copy(deep=True)
    original_events = [
        event.model_copy(deep=True)
        for event in app.session_state["review_state"].resolution_events
    ]
    edited_criterion = "User can export the edited research list as a downloadable CSV"

    app = app.text_input(key="criterion_text_AC-01").set_value(edited_criterion).run()
    app = app.button(key="confirm_criteria").click().run()

    pending_state = app.session_state["review_state"]
    assert pending_state.review.review_id == original_review_id
    assert pending_state.criteria_revision.number == 2
    assert len(pending_state.analysis_history) == 1
    assert len(pending_state.resolution_events) == len(original_events)

    app = app.button(key="run_analysis").click().run()
    state = app.session_state["review_state"]

    assert (
        state.review.review_id,
        state.criteria_revision.number,
        len(state.analysis_history),
        len(state.resolution_events),
    ) == (original_review_id, 2, 1, len(original_events))
    assert state.analysis_history == [original_bundle]
    assert state.resolution_events == original_events
    assert state.resolution_events[0].criteria_revision_number == 1
    assert state.bundle.criteria[0].text == edited_criterion
    assert state.review.final_acceptance is False
    assert state.bundle.review.final_acceptance is False
    assert app.session_state["bundle"] == state.bundle
    assert app.session_state["bundle"].review.review_id == original_review_id


def test_criteria_can_be_added_and_removed_before_reconfirmation() -> None:
    app = load_demo(new_app())
    app = app.text_input(key="new_criterion_text").set_value("Document export format").run()
    app = app.button(key="add_criterion_ui").click().run()

    assert len(app.session_state["criteria"]) == 5
    assert app.session_state["criteria"][-1].criterion_id == "AC-05"
    assert app.session_state["criteria_confirmed"] is False

    app = app.button(key="remove_AC-05").click().run()
    assert len(app.session_state["criteria"]) == 4


def test_evidence_matrix_filters_are_collapsed_without_changing_widget_contracts() -> None:
    app = analyzed_demo(new_app())
    filters = next(
        item for item in app.expander if item.label == "Filter evidence matrix (optional)"
    )

    assert filters.proto.expanded is False
    assert _main_widget_keys(filters) == [
        "status_filter",
        "priority_filter",
        "blocking_only",
        "evidence_level_filter",
    ]
    status_filter = app.multiselect(key="status_filter")
    priority_filter = app.multiselect(key="priority_filter")
    evidence_level_filter = app.multiselect(key="evidence_level_filter")

    assert status_filter.value == []
    assert status_filter.options == [
        "Strong candidate",
        "Weak candidate",
        "No candidate",
        "Analysis incomplete",
        "Reviewer verified",
        "Rejected",
    ]
    assert priority_filter.value == []
    assert priority_filter.options == ["Must Have", "Should Have"]
    assert app.checkbox(key="blocking_only").value is False
    assert evidence_level_filter.value == []
    assert evidence_level_filter.options == ["E0", "E1", "E2", "E3", "E4"]


def test_evidence_matrix_combines_blocker_and_evidence_level_filters() -> None:
    app = analyzed_demo(new_app())
    app = app.checkbox(key="blocking_only").check().run()
    app = app.multiselect(key="evidence_level_filter").select(EvidenceLevel.E2).run()

    assert evidence_matrix_criterion_ids(app) == ["AC-02"]


def test_evidence_matrix_reports_empty_filter_results() -> None:
    app = analyzed_demo(new_app())
    app = app.checkbox(key="blocking_only").check().run()
    app = app.multiselect(key="evidence_level_filter").select(EvidenceLevel.E4).run()

    assert evidence_matrix_criterion_ids(app) == []
    assert "No criteria match the current filters." in [item.value for item in app.info]
    markdown = [item.value for item in app.markdown]
    assert "[Review AC-01](#review-ac-01)" in markdown
    assert "#### Review AC-01" in markdown


def test_evidence_matrix_renders_as_reachable_cards_without_grid_tools() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    assert len(app.dataframe) == 0
    assert evidence_matrix_criterion_ids(app) == ["AC-01", "AC-02", "AC-03", "AC-04"]
    text_values = [item.value for item in app.text]
    assert "User can export the research list as CSV" in text_values
    assert "Successful export records research_exported" in text_values
    matrix_captions = [item.value for item in app.caption]
    assert "Requirement" in matrix_captions
    assert "Priority: Must have" in matrix_captions
    assert "Priority: Should have" in matrix_captions
    assert "Evidence status: Strong candidate" in matrix_captions
    assert "Evidence status: Weak candidate" in matrix_captions
    assert "Evidence status: No candidate" in matrix_captions
    assert "Evidence types: Implementation, Test" in matrix_captions
    assert "Evidence types: None" in matrix_captions
    assert matrix_captions.count("Reviewer decision: Unresolved") == 4
    assert not any("Confidence:" in value for value in matrix_captions)
    assert not any("Concern:" in value for value in matrix_captions)


def test_evidence_matrix_cards_explain_and_open_each_criterion() -> None:
    app = analyzed_demo(new_app())
    state = app.session_state["review_state"]
    assert state.bundle is not None

    rendered_text = [item.value for item in app.text]
    rendered_code = [item.value for item in app.code]
    matrix_captions = [item.value for item in app.caption]
    for finding in state.bundle.findings:
        assert f"Candidate count: {len(finding.evidence_ids)}" in matrix_captions
        assert finding.reason in rendered_text
        assert finding.recommended_action in rendered_code
        for missing in finding.missing_evidence:
            assert missing in rendered_text
        assert app.button(key=f"inspect_matrix_{finding.criterion_id}").label == (
            "Inspect this criterion"
        )

    app = app.button(key="inspect_matrix_AC-03").click().run()

    assert app.selectbox(key="selected_criterion").value == "AC-03"
    selected_text = [item.value for item in app.text]
    assert "Failed export shows an error message" in selected_text


def test_invalid_detail_target_defaults_to_first_unresolved_blocker() -> None:
    assert default_criterion_detail_id(
        criterion_ids=["AC-01", "AC-02", "AC-03"],
        unresolved_ids=["AC-02", "AC-03"],
        blocking_ids={"AC-02", "AC-03"},
        selected_id="AC-99",
    ) == "AC-02"


def test_unresolved_criterion_priority_stably_places_blockers_first() -> None:
    assert prioritize_unresolved_criterion_ids(
        unresolved_ids=["AC-01", "AC-02", "AC-03", "AC-04"],
        blocking_ids={"AC-02", "AC-03"},
    ) == ["AC-02", "AC-03", "AC-01", "AC-04"]


def test_empty_detail_target_defaults_to_first_unresolved_blocker() -> None:
    assert default_criterion_detail_id(
        criterion_ids=["AC-01", "AC-02", "AC-03"],
        unresolved_ids=["AC-02", "AC-03"],
        blocking_ids={"AC-02", "AC-03"},
        selected_id=None,
    ) == "AC-02"


def test_criterion_detail_preserves_deep_matrix_context_without_duplicate_summary() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="selected_criterion").set_value("AC-01").run()
    markdown_text = [item.value for item in app.markdown]
    visible_markdown = "\n".join(markdown_text)
    text_values = [item.value for item in app.text]

    assert "E1" in text_values
    assert "E2" in text_values
    assert "High" in text_values
    assert "4" in text_values
    assert "Unresolved" in text_values
    assert (
        "Strong candidate evidence was found; a reviewer must still judge sufficiency."
        in text_values
    )
    assert "**AC-01 — Evidence Found** · User can export the research list as CSV" not in (
        visible_markdown
    )


def test_ordinary_resolution_precedes_optional_external_verification() -> None:
    app = analyzed_demo(new_app())
    keys = _main_widget_keys(app)
    optional = next(
        item
        for item in app.expander
        if item.label == "Record optional external verification (E3/E4)"
    )

    assert keys.index("decision_reviewer") < keys.index("resolution_decision")
    assert keys.index("save_resolution") < keys.index("runtime_artifact_reference")
    assert keys.index("runtime_artifact_reference") < keys.index("save_runtime_evidence")
    assert optional.proto.expanded is False


def test_candidate_evidence_groups_by_path_and_type_without_losing_items() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="selected_criterion").set_value("AC-01").run()
    groups = [item for item in app.expander if item.label.startswith("Evidence group ")]

    assert [item.label for item in groups] == [
        "Evidence group 1 · Implementation · 2 items",
        "Evidence group 2 · Test · 2 items",
    ]
    assert [groups[0].code[0].value, groups[1].code[0].value] == [
        "src/export.py",
        "tests/test_export.py",
    ]
    rendered_ids = [
        value
        for group in groups
        for value in [item.value for item in group.code]
        if value.startswith("EV-")
    ]
    assert rendered_ids == [
        "EV-AC-01-01",
        "EV-AC-01-04",
        "EV-AC-01-02",
        "EV-AC-01-03",
    ]


def test_selected_requirement_and_candidate_values_are_not_raw_markdown() -> None:
    app = analyzed_demo(new_app())
    selected_text = app.session_state["criteria"][0].text
    markdown_values = [item.value for item in app.markdown]

    assert selected_text in [item.value for item in app.text]
    assert all(selected_text not in value for value in markdown_values)


def test_evidence_matrix_shows_current_human_resolution() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.ACCEPTED).run()
    app = app.button(key="save_resolution").click().run()
    app = app.run()

    assert "Reviewer decision: Accepted" in [item.value for item in app.caption]


def test_accepting_below_required_evidence_requires_an_auditable_note() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()
    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.ACCEPTED
    ).run()

    assert "Accept despite insufficient candidate evidence" in [
        item.value for item in app.warning
    ]
    assert "Required E1 · observed E0" in [item.value for item in app.caption]
    assert app.button(key="save_resolution").disabled is True

    app = app.text_area(key="resolution_note").set_value(
        "Accepted after inspecting external context not represented by candidates."
    ).run()

    assert app.button(key="save_resolution").disabled is False


def test_non_acceptance_below_required_evidence_does_not_require_a_note() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()
    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.CHANGE_REQUIRED
    ).run()

    assert app.button(key="save_resolution").disabled is False
    assert "Accept despite insufficient candidate evidence" not in [
        item.value for item in app.warning
    ]


def test_successful_resolution_save_clears_form_and_prevents_accidental_repeat() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.ACCEPTED).run()
    app = app.text_area(key="resolution_note").set_value("Evidence reviewed").run()
    app = app.button(key="save_resolution").click().run()

    state = app.session_state["review_state"]
    assert len(state.resolution_events) == 1
    assert app.selectbox(key="resolution_decision").value is None
    assert app.text_area(key="resolution_note").value == ""
    assert app.button(key="save_resolution").disabled is True
    assert "Human resolution appended to the local review history." in [
        message.value for message in app.success
    ]


def test_criterion_resolution_failure_preserves_retryable_state_without_raw_details() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.ACCEPTED).run()
    app = app.text_area(key="resolution_note").set_value("Controlled reviewer note").run()
    review_state = app.session_state["review_state"].model_copy(deep=True)
    raw_error = "invalid resolution at /private/secret/resolution.json"

    with patch(
        "scopeproof_core.reviews.lifecycle.append_resolution",
        side_effect=ValueError(raw_error),
    ):
        app = app.button(key="save_resolution").click().run()

    recovery = (
        "Criterion resolution could not be recorded. The review remains unchanged. Verify the "
        "active review state and try again."
    )
    assert recovery in [item.value for item in app.error]
    assert not app.exception
    rendered = "\n".join(
        item.value
        for item in [
            *app.error,
            *app.warning,
            *app.info,
            *app.success,
            *app.caption,
            *app.markdown,
            *app.code,
        ]
    )
    assert raw_error not in rendered
    assert "/private/secret/resolution.json" not in rendered
    assert app.session_state["review_state"] == review_state
    assert app.session_state["bundle"] == review_state.bundle
    assert app.session_state["saved_review_fingerprint"] == (
        _review_fingerprint_for_test(review_state)
    )
    assert app.session_state["review_state"].resolution_events == []
    assert app.selectbox(key="resolution_decision").value is HumanDecision.ACCEPTED
    assert app.text_area(key="resolution_note").value == "Controlled reviewer note"
    assert app.button(key="save_resolution").disabled is False
    assert "Human resolution appended" not in "\n".join(
        item.value for item in app.success
    )


def test_manual_verification_is_only_available_through_external_verification() -> None:
    app = analyzed_demo(new_app())
    assert "Manually Verified" not in app.selectbox(key="resolution_decision").options
    assert app.button(key="save_runtime_evidence").label == "Save external verification"


def test_criterion_resolution_context_identifies_target_and_boundary() -> None:
    app = analyzed_demo(new_app())
    caption_text = "\n".join(caption.value for caption in app.caption)

    assert "### Criterion resolution" in [item.value for item in app.markdown]
    assert "This decision will be recorded for the selected criterion above." in caption_text
    assert "It does not record final review acceptance." in caption_text
    assert "User can export the research list as CSV" in [item.value for item in app.text]
    assert "Select a decision to see its deterministic gate impact." in caption_text

    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()
    assert "Failed export shows an error message" in [item.value for item in app.text]


def test_criterion_detail_labels_candidate_evidence_and_recovery_guidance() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="selected_criterion").set_value("AC-01").run()
    bundle = app.session_state["review_state"].bundle
    finding = next(item for item in bundle.findings if item.criterion_id == "AC-01")
    evidence = next(item for item in bundle.evidence if item.evidence_id in finding.evidence_ids)

    markdown_text = "\n".join(item.value for item in app.markdown)
    caption_text = "\n".join(item.value for item in app.caption)
    code_text = "\n".join(item.value for item in app.code)
    text_values = [item.value for item in app.text]

    assert "Recommended next action" in markdown_text
    assert finding.recommended_action in code_text
    assert "Candidate evidence" in markdown_text
    assert "Matching rationale" in caption_text
    assert evidence.relevance_reason in text_values
    assert "Matching rule" in caption_text
    assert evidence.matching_rule in text_values
    assert "Limitation" in caption_text
    assert evidence.limitations[0] in text_values
    assert evidence.excerpt in [item.value for item in app.code]
    assert f"](<{evidence.permalink}>)" in markdown_text


def test_missing_criterion_detail_shows_action_and_no_candidate_state() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()
    bundle = app.session_state["review_state"].bundle
    finding = next(item for item in bundle.findings if item.criterion_id == "AC-03")

    markdown_text = "\n".join(item.value for item in app.markdown)
    code_text = "\n".join(item.value for item in app.code)
    caption_text = "\n".join(item.value for item in app.caption)

    assert "Recommended next action" in markdown_text
    assert finding.recommended_action in code_text
    assert "Candidate evidence" in markdown_text
    assert "No candidate evidence is linked to this provisional finding." in caption_text


def test_criterion_detail_explains_retrieval_without_presenting_it_as_evidence() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()

    markdown_text = "\n".join(item.value for item in app.markdown)
    caption_text = "\n".join(item.value for item in app.caption)
    text_values = [item.value for item in app.text]

    assert "How ScopeProof searched" in markdown_text
    assert "Search outcome" in caption_text
    assert "Below Relevance Threshold" in text_values
    assert "Searched terms" in caption_text
    assert "Searched paths" in caption_text
    assert (
        "Search diagnostics explain retrieval; they are not evidence that the criterion "
        "is satisfied or missing from the repository."
    ) in caption_text


def test_compound_criterion_can_be_split_in_workbench() -> None:
    app = new_app()
    app = app.text_area(key="requirements_input").set_value("Export CSV and record analytics").run()
    app = app.button(key="prepare_criteria").click().run()
    app = app.text_area(key="split_criterion_text").set_value("Export CSV\nRecord analytics").run()
    app = app.button(key="split_criterion_ui").click().run()

    assert [(item.criterion_id, item.text) for item in app.session_state["criteria"]] == [
        ("AC-01", "Export CSV"),
        ("AC-02", "Record analytics"),
    ]


def test_human_decision_and_final_acceptance_append_history() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.ACCEPTED).run()
    app = app.button(key="save_resolution").click().run()
    app = resolve_all_criteria(app)
    app = app.button(key="record_final_acceptance").click().run()

    state = app.session_state["review_state"]
    assert len(state.resolution_events) == len(state.criteria_revision.criteria) + 1
    assert state.review.final_acceptance is True
    assert "Resolution history" in "\n".join(markdown.value for markdown in app.markdown)


def test_resolution_history_distinguishes_current_and_superseded_decisions() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.REJECTED_FINDING).run()
    app = app.button(key="save_resolution").click().run()
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.ACCEPTED).run()
    app = app.button(key="save_resolution").click().run()

    text_values = [item.value for item in app.text]
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Superseded · revision 1" in text_values
    assert "Current · revision 1" in text_values
    assert "Rejected Finding" in text_values
    assert "Accepted" in text_values
    assert (
        "Current events are the latest recorded inputs for the active revision. Superseded and "
        "prior-revision events remain audit history and do not independently control the gate."
    ) in caption_text


def test_resolution_history_shows_reviewer_timestamp_and_claimed_level() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="selected_criterion").set_value("AC-01").run()
    review_state = app.session_state["review_state"].model_copy(deep=True)
    recorded_at = datetime(2026, 7, 14, 19, 45, tzinfo=UTC)
    review_state = append_external_verification(
        review_state,
        RuntimeEvidence(
            runtime_evidence_id="runtime-audit-event",
            repository=review_state.review.repository,
            pr_number=review_state.review.pr_number,
            head_sha=review_state.review.head_sha,
            criterion_id="AC-01",
            artifact_reference="https://example.test/run/manual-audit-event",
            scenario="Controlled verification scenario",
            environment="staging",
            result="passed",
            reviewer="Controlled reviewer",
            evidence_level=EvidenceLevel.E3,
            timestamp=recorded_at,
        ),
        ResolutionEvent(
            event_id="manual-audit-event",
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            comment="Controlled verification note",
            reviewer="Controlled reviewer",
            claimed_evidence_level=EvidenceLevel.E3,
            runtime_evidence_id="runtime-audit-event",
            timestamp=recorded_at,
            criteria_revision_number=1,
        ),
    )
    app.session_state["review_state"] = review_state
    app.session_state["bundle"] = review_state.bundle
    app = app.run()

    text_values = [item.value for item in app.text]
    assert "Controlled reviewer" in text_values
    assert "2026-07-14T19:45:00Z" in text_values
    assert "E3" in text_values
    assert [item.value for item in app.code].count("runtime-audit-event") == 2


def test_resolution_history_omits_claimed_level_for_non_manual_decision() -> None:
    app = analyzed_demo(new_app())
    review_state = app.session_state["review_state"].model_copy(deep=True)
    review_state = append_resolution(
        review_state,
        ResolutionEvent(
            event_id="accepted-audit-event",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            comment="Controlled acceptance note",
            reviewer="Controlled reviewer",
            timestamp=datetime(2026, 7, 14, 19, 50, tzinfo=UTC),
            criteria_revision_number=1,
        ),
    )
    app.session_state["review_state"] = review_state
    app.session_state["bundle"] = review_state.bundle
    app = app.run()

    captions = [item.value for item in app.caption]
    text_values = [item.value for item in app.text]
    assert "Controlled reviewer" in text_values
    assert "2026-07-14T19:50:00Z" in text_values
    assert "Claimed evidence level" not in captions


def test_runtime_evidence_guidance_lists_only_missing_required_fields() -> None:
    app = analyzed_demo(new_app())

    guidance = [
        caption.value
        for caption in app.caption
        if caption.value.startswith("Complete required fields to enable Save:")
    ]
    assert guidance == [
        "Complete required fields to enable Save: Artifact or URL, Runtime scenario, "
        "Environment, Observed result, Runtime reviewer."
    ]
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/1"
    ).run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()

    guidance = [
        caption.value
        for caption in app.caption
        if caption.value.startswith("Complete required fields to enable Save:")
    ]
    assert guidance == [
        "Complete required fields to enable Save: Observed result, Runtime reviewer."
    ]
    assert app.button(key="save_runtime_evidence").disabled is True


def test_runtime_evidence_guidance_disappears_when_save_is_ready() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value("   ").run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()
    app = app.text_area(key="runtime_limitations").set_value("Browser only").run()

    guidance = "\n".join(caption.value for caption in app.caption)
    assert "Complete required fields to enable Save: Artifact or URL." in guidance
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/1"
    ).run()

    guidance = "\n".join(caption.value for caption in app.caption)
    assert "Complete required fields to enable Save:" not in guidance
    assert app.button(key="save_runtime_evidence").disabled is False


def test_runtime_evidence_save_requires_all_required_fields() -> None:
    app = analyzed_demo(new_app())
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value("   ").run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/1"
    ).run()
    assert app.button(key="save_runtime_evidence").disabled is False


def test_runtime_evidence_fields_identify_required_and_optional_status() -> None:
    app = analyzed_demo(new_app())

    assert app.text_input(key="runtime_artifact_reference").label == (
        "Artifact or URL (required)"
    )
    assert app.text_area(key="runtime_scenario").label == "Runtime scenario (required)"
    assert app.text_input(key="runtime_environment").label == "Environment (required)"
    assert app.text_input(key="runtime_result").label == "Observed result (required)"
    assert app.text_input(key="runtime_reviewer").label == "Runtime reviewer (required)"
    assert app.text_area(key="runtime_limitations").label == (
        "Runtime limitations (optional)"
    )
    assert app.button(key="save_runtime_evidence").disabled is True
    assert (
        "This records a review-level acceptance event. It does not resolve individual criteria "
        "or override the deterministic gate. Review every criterion and its evidence before "
        "recording final acceptance."
    ) in [caption.value for caption in app.caption]


def test_runtime_evidence_prerequisite_guidance_is_visible() -> None:
    app = analyzed_demo(new_app())
    caption_text = "\n".join(caption.value for caption in app.caption)
    assert (
        "Artifact, scenario, environment, observed result, and reviewer are required"
        in caption_text
    )
    assert "Limitations are optional" in caption_text


def test_runtime_evidence_validation_failure_is_safe_and_retryable() -> None:
    app = analyzed_demo(new_app())
    values = {
        "runtime_artifact_reference": "artifact-controlled",
        "runtime_scenario": "Controlled scenario",
        "runtime_environment": "controlled environment",
        "runtime_result": "controlled result",
        "runtime_reviewer": "controlled reviewer",
    }
    app = app.text_input(key="runtime_artifact_reference").set_value(
        values["runtime_artifact_reference"]
    ).run()
    app = app.text_area(key="runtime_scenario").set_value(
        values["runtime_scenario"]
    ).run()
    for key in ("runtime_environment", "runtime_result", "runtime_reviewer"):
        app = app.text_input(key=key).set_value(values[key]).run()
    review_state = app.session_state["review_state"].model_copy(deep=True)
    raw_error = "2 validation errors at /private/secret/runtime.json"

    with patch(
        "scopeproof_core.reviews.lifecycle.append_external_verification",
        side_effect=ValueError(raw_error),
    ):
        app = app.button(key="save_runtime_evidence").click().run()

    recovery = (
        "External verification could not be saved. Check every required field and select E3 or E4."
    )
    assert recovery in [item.value for item in app.error]
    assert not app.exception
    rendered = "\n".join(
        item.value
        for item in [
            *app.error,
            *app.warning,
            *app.info,
            *app.success,
            *app.caption,
            *app.markdown,
            *app.code,
        ]
    )
    assert raw_error not in rendered
    assert "/private/secret/runtime.json" not in rendered
    assert app.session_state["review_state"] == review_state
    assert app.session_state["saved_review_fingerprint"] == (
        _review_fingerprint_for_test(review_state)
    )
    assert app.session_state["review_state"].bundle.runtime_evidence == []
    assert app.text_input(key="runtime_artifact_reference").value == values[
        "runtime_artifact_reference"
    ]
    assert app.text_area(key="runtime_scenario").value == values["runtime_scenario"]
    for key in ("runtime_environment", "runtime_result", "runtime_reviewer"):
        assert app.text_input(key=key).value == values[key]
    assert app.button(key="save_runtime_evidence").disabled is False
    assert "Manual runtime evidence appended" not in "\n".join(
        item.value for item in app.success
    )


def test_runtime_evidence_context_identifies_criterion_and_explains_levels() -> None:
    app = analyzed_demo(new_app())
    target_context = next(
        caption.value
        for caption in app.caption
        if caption.value.startswith("This record will be attached to")
    )
    assert target_context == "This record will be attached to the selected criterion."
    assert "User can export the research list as CSV" in [item.value for item in app.text]
    assert "Record a human-supplied observation only." in "\n".join(
        item.value for item in app.caption
    )

    level_context = next(
        caption.value
        for caption in app.caption
        if caption.value.startswith("E3 means manually recorded external runtime verification")
    )
    assert (
        "E3 means manually recorded external runtime verification. "
        "E4 means explicit human acceptance. Saving resolves this criterion as manually "
        "verified but does not record final review acceptance."
    ) in level_context
    assert (
        "Artifact, scenario, environment, observed result, and reviewer are required."
        in level_context
    )
    assert "Limitations are optional." in level_context

    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()
    target_captions = [
        caption.value
        for caption in app.caption
        if caption.value.startswith("This record will be attached to")
    ]
    assert len(target_captions) == 1
    assert target_captions[0] == "This record will be attached to the selected criterion."
    assert "Failed export shows an error message" in [item.value for item in app.text]


def test_criterion_change_clears_pending_target_specific_drafts() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value(
        "artifact-for-ac-01"
    ).run()
    app = app.text_area(key="runtime_scenario").set_value(
        "AC-01 export scenario"
    ).run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()
    app = app.selectbox(key="runtime_evidence_level").set_value(EvidenceLevel.E4).run()
    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.ACCEPTED
    ).run()
    app = app.text_area(key="resolution_note").set_value(
        "Verified AC-01 in staging."
    ).run()

    assert app.button(key="save_runtime_evidence").disabled is False
    assert app.button(key="save_resolution").disabled is False

    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()

    assert app.text_input(key="runtime_artifact_reference").value == ""
    assert app.text_area(key="runtime_scenario").value == ""
    assert app.text_input(key="runtime_environment").value == ""
    assert app.text_input(key="runtime_result").value == ""
    assert app.text_input(key="runtime_reviewer").value == ""
    assert app.text_area(key="runtime_limitations").value == ""
    assert app.selectbox(key="runtime_evidence_level").value is EvidenceLevel.E3
    assert app.button(key="save_runtime_evidence").disabled is True
    assert app.selectbox(key="resolution_decision").value is None
    assert app.text_area(key="resolution_note").value == ""
    assert "manual_evidence_level" not in app.session_state.filtered_state
    assert app.button(key="save_resolution").disabled is True
    assert app.session_state["review_state"].bundle.runtime_evidence == []
    assert app.session_state["review_state"].resolution_events == []
    assert (
        "Unsaved runtime evidence or resolution inputs were cleared because the review "
        "target changed. Re-enter them for AC-03 before saving."
    ) in [item.value for item in app.info]


def test_clean_criterion_change_does_not_claim_a_draft_was_cleared() -> None:
    app = analyzed_demo(new_app())

    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()

    assert (
        "Unsaved runtime evidence or resolution inputs were cleared because the review "
        "target changed."
    ) not in "\n".join(item.value for item in app.info)


def test_manual_runtime_evidence_can_be_recorded_without_changing_static_findings() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    finding_status = app.session_state["review_state"].bundle.findings[0].status
    app = app.text_input(key="runtime_artifact_reference").set_value("https://example.test/run/1").run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()
    app = app.button(key="save_runtime_evidence").click().run()

    bundle = app.session_state["review_state"].bundle
    assert bundle.findings[0].status is finding_status
    assert bundle.runtime_evidence[0].artifact_reference.endswith("/1")


def test_external_verification_normalizes_reviewer_for_atomic_records() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/normalized-reviewer"
    ).run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("  QA  ").run()

    app = app.button(key="save_runtime_evidence").click().run()

    review_state = app.session_state["review_state"]
    manual_events = [
        event
        for event in review_state.resolution_events
        if event.decision is HumanDecision.MANUALLY_VERIFIED
    ]
    assert len(review_state.bundle.runtime_evidence) == 1
    assert len(manual_events) == 1
    runtime_item = review_state.bundle.runtime_evidence[0]
    assert runtime_item.reviewer == "QA"
    assert manual_events[0].reviewer == "QA"
    assert UUID(runtime_item.runtime_evidence_id).version == 4
    assert (
        runtime_item.repository,
        runtime_item.pr_number,
        runtime_item.head_sha,
    ) == (
        review_state.review.repository,
        review_state.review.pr_number,
        review_state.review.head_sha,
    )
    assert manual_events[0].runtime_evidence_id == runtime_item.runtime_evidence_id
    identity_widget_keys = {
        "runtime_evidence_id",
        "runtime_repository",
        "runtime_pr_number",
        "runtime_head_sha",
    }
    assert identity_widget_keys.isdisjoint(
        {item.key for item in [*app.text_input, *app.number_input]}
    )


def test_runtime_evidence_record_renders_bound_identity_as_non_editable_text() -> None:
    app = analyzed_demo(new_app())
    review = app.session_state["review_state"].review.model_copy(deep=True)
    app = app.text_input(key="runtime_artifact_reference").set_value("artifact-identity").run()
    app = app.text_area(key="runtime_scenario").set_value("Identity scenario").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("observed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()

    app = app.button(key="save_runtime_evidence").click().run()

    runtime_item = app.session_state["review_state"].bundle.runtime_evidence[0]
    assert runtime_item.runtime_evidence_id in [item.value for item in app.code]
    assert f"{review.repository} · PR #{review.pr_number}" in [
        item.value for item in app.text
    ]
    assert review.head_sha in [item.value for item in app.code]
    assert "Runtime evidence identity is bound automatically to the active review." in [
        item.value for item in app.caption
    ]


def test_runtime_evidence_legacy_unlinked_warning_disables_final_acceptance() -> None:
    app = analyzed_demo(new_app())
    review_state = app.session_state["review_state"].model_copy(deep=True)
    runtime_item = RuntimeEvidence(
        runtime_evidence_id="migrated-runtime-id",
        repository=review_state.review.repository,
        pr_number=review_state.review.pr_number,
        head_sha=review_state.review.head_sha,
        criterion_id="AC-01",
        artifact_reference="artifact-migrated",
        scenario="Migrated legacy scenario",
        environment="staging",
        result="observed",
        reviewer="Legacy QA",
        evidence_level=EvidenceLevel.E3,
    )
    review_state = append_external_verification(
        review_state,
        runtime_item,
        ResolutionEvent(
            event_id="migrated-manual-event",
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            comment="Migrated manual verification",
            claimed_evidence_level=EvidenceLevel.E3,
            runtime_evidence_id=runtime_item.runtime_evidence_id,
            reviewer=runtime_item.reviewer,
        ),
    )
    review_state.resolution_events[-1].runtime_evidence_id = None
    review_state.bundle.resolutions[0].runtime_evidence_id = None
    review_state.bundle.gate = evaluate_gate(
        review_state.bundle.review,
        review_state.bundle.criteria,
        review_state.bundle.findings,
        review_state.bundle.resolutions,
    )
    app.session_state["review_state"] = review_state
    app.session_state["bundle"] = review_state.bundle

    app = app.run()

    warning = "Legacy unlinked; re-record at the active head"
    assert warning in [item.value for item in app.warning]
    assert app.button(key="record_final_acceptance").disabled is True


def test_reopened_legacy_verification_can_revoke_reverify_and_reaccept(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = analyzed_demo(new_app())
    state = app.session_state["review_state"].model_copy(deep=True)
    assert state.bundle is not None
    legacy_runtime = RuntimeEvidence(
        runtime_evidence_id="legacy-runtime",
        repository=state.review.repository,
        pr_number=state.review.pr_number,
        head_sha=state.review.head_sha,
        criterion_id="AC-01",
        artifact_reference="https://example.test/runs/legacy",
        scenario="Legacy export scenario",
        environment="legacy staging",
        result="passed",
        reviewer="Legacy reviewer",
        evidence_level=EvidenceLevel.E3,
        limitations=["Legacy observation retained for audit"],
    )
    state = append_external_verification(
        state,
        legacy_runtime,
        ResolutionEvent(
            event_id="legacy-manual-event",
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            comment="Legacy manual verification note",
            claimed_evidence_level=EvidenceLevel.E3,
            runtime_evidence_id=legacy_runtime.runtime_evidence_id,
            reviewer=legacy_runtime.reviewer,
        ),
    )
    for criterion in state.bundle.criteria:
        if criterion.criterion_id == "AC-01":
            continue
        state = append_resolution(
            state,
            ResolutionEvent(
                event_id=f"legacy-accepted-{criterion.criterion_id}",
                criterion_id=criterion.criterion_id,
                decision=HumanDecision.ACCEPTED,
                comment=f"Legacy acceptance for {criterion.criterion_id}",
                reviewer="Legacy reviewer",
            ),
        )
    state = append_resolution(
        state,
        ResolutionEvent(
            event_id="legacy-final-acceptance",
            final_acceptance=True,
            comment="Legacy final acceptance note",
            reviewer="Legacy reviewer",
        ),
    )
    review_id = state.review.review_id
    store = JsonReviewStore(default_local_review_directory())
    record_path = store.save(state)
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    payload["record_version"] = 2
    for runtime_item in payload["state"]["bundle"]["runtime_evidence"]:
        for field_name in (
            "runtime_evidence_id",
            "repository",
            "pr_number",
            "head_sha",
        ):
            runtime_item.pop(field_name)
    for resolution in payload["state"]["bundle"]["resolutions"]:
        resolution.pop("runtime_evidence_id", None)
    for event in payload["state"]["resolution_events"]:
        event.pop("runtime_evidence_id", None)
    record_path.write_text(json.dumps(payload), encoding="utf-8")

    reopened = select_saved_review(new_app(), review_id)
    reopened = reopened.button(key="reopen_review").click().run()

    warning = "Legacy unlinked; re-record at the active head"
    assert warning in [item.value for item in reopened.warning]
    assert (
        "Revoke final acceptance before recording new E3/E4 verification at the active head."
        in [item.value for item in reopened.warning]
    )
    assert reopened.button(key="record_final_acceptance").disabled is True
    reopened = reopened.text_input(key="decision_reviewer").set_value("   ").run()
    assert reopened.button(key="revoke_final_acceptance").disabled is True
    reopened = reopened.text_input(key="decision_reviewer").set_value(
        "  Recovery reviewer  "
    ).run()
    assert reopened.button(key="revoke_final_acceptance").disabled is False
    reopened = reopened.text_input(key="runtime_artifact_reference").set_value(
        "pending-artifact"
    ).run()
    assert reopened.button(key="revoke_final_acceptance").disabled is True
    reopened = reopened.button(key="clear_criterion_detail_drafts").click().run()
    reopened = reopened.text_input(key="decision_reviewer").set_value(
        "  Recovery reviewer  "
    ).run()
    assert reopened.button(key="revoke_final_acceptance").disabled is False

    event_count_before_recovery = len(
        reopened.session_state["review_state"].resolution_events
    )
    reopened = reopened.button(key="revoke_final_acceptance").click().run()
    revoked = reopened.session_state["review_state"]
    assert revoked.review.final_acceptance is False
    assert revoked.resolution_events[-1].final_acceptance is False
    assert revoked.resolution_events[-1].reviewer == "Recovery reviewer"
    assert len(revoked.resolution_events) == event_count_before_recovery + 1
    assert JsonReviewStore(default_local_review_directory()).load(review_id) == revoked

    reopened = select_saved_review(new_app(), review_id)
    reopened = reopened.button(key="reopen_review").click().run()
    assert reopened.session_state["review_state"] == revoked
    reopened = reopened.text_input(key="decision_reviewer").set_value(
        "  Recovery reviewer  "
    ).run()
    reopened = reopened.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/runs/recovery"
    ).run()
    reopened = reopened.text_area(key="runtime_scenario").set_value(
        "Reverify export at the current head"
    ).run()
    reopened = reopened.text_input(key="runtime_environment").set_value(
        "current staging"
    ).run()
    reopened = reopened.text_input(key="runtime_result").set_value("passed").run()
    reopened = reopened.text_input(key="runtime_reviewer").set_value(
        "  Recovery reviewer  "
    ).run()
    reopened = reopened.button(key="save_runtime_evidence").click().run()

    reverified = reopened.session_state["review_state"]
    new_runtime = reverified.bundle.runtime_evidence[-1]
    assert new_runtime.head_sha == reverified.review.head_sha
    assert new_runtime.runtime_evidence_id is not None
    assert reverified.resolution_events[-1].decision is HumanDecision.MANUALLY_VERIFIED
    assert (
        reverified.resolution_events[-1].runtime_evidence_id
        == new_runtime.runtime_evidence_id
    )
    assert reopened.button(key="record_final_acceptance").disabled is False

    reopened = reopened.button(key="record_final_acceptance").click().run()
    recovered = reopened.session_state["review_state"]
    assert recovered.review.final_acceptance is True
    assert recovered.bundle.gate.verdict is GateVerdict.READY
    assert [
        (event.final_acceptance, event.decision)
        for event in recovered.resolution_events[-3:]
    ] == [
        (False, None),
        (None, HumanDecision.MANUALLY_VERIFIED),
        (True, None),
    ]
    assert [
        event.reviewer for event in recovered.resolution_events[-3:]
    ] == ["Recovery reviewer"] * 3
    assert JsonReviewStore(default_local_review_directory()).load(review_id) == recovered

    final_reopen = select_saved_review(new_app(), review_id)
    final_reopen = final_reopen.button(key="reopen_review").click().run()
    assert final_reopen.session_state["review_state"] == recovered
    download_keys = [button.key for button in final_reopen.download_button]
    assert download_keys == ["download_markdown", "download_json", "download_csv"]
    assert all(
        not final_reopen.download_button(key=key).disabled for key in download_keys
    )


def test_runtime_artifact_identifier_renders_as_plain_text() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value("artifact-42").run()
    app = app.text_area(key="runtime_scenario").set_value("Fixture scenario").run()
    app = app.text_input(key="runtime_environment").set_value("Fixture environment").run()
    app = app.text_input(key="runtime_result").set_value("Fixture result").run()
    app = app.text_input(key="runtime_reviewer").set_value("Fixture reviewer").run()
    app = app.button(key="save_runtime_evidence").click().run()

    runtime_rows = [
        item.value.replace("\\", "") for item in app.markdown if "artifact\\-42" in item.value
    ]
    assert runtime_rows == ["artifact-42"]
    assert "Fixture scenario" in [item.value for item in app.text]


def test_runtime_record_shows_reviewer_and_limitations() -> None:
    app = analyzed_demo(new_app())
    app = (
        app.text_input(key="runtime_artifact_reference").set_value("artifact-complete-record").run()
    )
    app = app.text_area(key="runtime_scenario").set_value("Controlled export scenario").run()
    app = app.text_input(key="runtime_environment").set_value("Controlled environment").run()
    app = app.text_input(key="runtime_result").set_value("Controlled observed result").run()
    app = app.text_input(key="runtime_reviewer").set_value("Controlled reviewer").run()
    app = (
        app.text_area(key="runtime_limitations")
        .set_value("Browser-only observation\nMobile behavior not observed")
        .run()
    )

    app = app.button(key="save_runtime_evidence").click().run()

    rendered_markdown = [item.value.replace("\\", "") for item in app.markdown]
    rendered_text = [item.value for item in app.text]
    captions = [item.value for item in app.caption]
    assert "artifact-complete-record" in rendered_markdown
    assert "Controlled export scenario" in rendered_text
    assert "Controlled environment" in rendered_text
    assert "Controlled observed result" in rendered_text
    assert "E3" in rendered_text
    assert "Controlled reviewer" in rendered_text
    assert "Limitations" in captions
    assert "Browser-only observation" in rendered_text
    assert "Mobile behavior not observed" in rendered_text
    assert "No limitations recorded." not in [item.value for item in app.caption]


def test_runtime_record_shows_persisted_utc_timestamp() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value("artifact-timestamped").run()
    app = app.text_area(key="runtime_scenario").set_value("Controlled timestamp scenario").run()
    app = app.text_input(key="runtime_environment").set_value("Controlled environment").run()
    app = app.text_input(key="runtime_result").set_value("Controlled observed result").run()
    app = app.text_input(key="runtime_reviewer").set_value("Controlled reviewer").run()
    app = app.button(key="save_runtime_evidence").click().run()

    review_state = app.session_state["review_state"].model_copy(deep=True)
    review_state.bundle.runtime_evidence[0].timestamp = datetime(2026, 7, 14, 12, 10, tzinfo=UTC)
    app.session_state["review_state"] = review_state
    app.session_state["bundle"] = review_state.bundle
    app = app.run()

    assert "2026-07-14T12:10:00Z" in [item.value for item in app.text]


def test_runtime_record_shows_explicit_empty_limitations_state() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value(
        "artifact-no-limitations"
    ).run()
    app = app.text_area(key="runtime_scenario").set_value(
        "Controlled export scenario"
    ).run()
    app = app.text_input(key="runtime_environment").set_value(
        "Controlled environment"
    ).run()
    app = app.text_input(key="runtime_result").set_value(
        "Controlled observed result"
    ).run()
    app = app.text_input(key="runtime_reviewer").set_value(
        "Controlled reviewer"
    ).run()

    app = app.button(key="save_runtime_evidence").click().run()

    assert "No limitations recorded." in [item.value for item in app.caption]


def test_successful_runtime_evidence_save_clears_form_and_prevents_accidental_repeat() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/reset"
    ).run()
    app = app.text_area(key="runtime_scenario").set_value("Fixture scenario").run()
    app = app.text_input(key="runtime_environment").set_value("Fixture environment").run()
    app = app.text_input(key="runtime_result").set_value("Fixture result").run()
    app = app.text_input(key="runtime_reviewer").set_value("Fixture reviewer").run()
    app = app.text_area(key="runtime_limitations").set_value("Fixture limitation").run()
    app = app.selectbox(key="runtime_evidence_level").set_value(EvidenceLevel.E4).run()

    app = app.button(key="save_runtime_evidence").click().run()

    assert len(app.session_state["review_state"].bundle.runtime_evidence) == 1
    assert app.text_input(key="runtime_artifact_reference").value == ""
    assert app.text_area(key="runtime_scenario").value == ""
    assert app.text_input(key="runtime_environment").value == ""
    assert app.text_input(key="runtime_result").value == ""
    assert app.text_input(key="runtime_reviewer").value == ""
    assert app.text_area(key="runtime_limitations").value == ""
    assert app.selectbox(key="runtime_evidence_level").value is EvidenceLevel.E3
    assert app.button(key="save_runtime_evidence").disabled is True
    assert "External verification and reviewer decision recorded together." in [
        item.value for item in app.success
    ]


def test_junit_import_maps_uploaded_suite_without_changing_gate_or_decisions() -> None:
    app = analyzed_exact_head_standard_demo(new_app())
    before = app.session_state["review_state"].model_copy(deep=True)
    assert before.bundle is not None
    assert (
        app.file_uploader(key="junit_artifact_upload").proto.max_upload_size_mb
        == 1
    )

    app = app.file_uploader(key="junit_artifact_upload").upload(
        "results.xml",
        b'<testsuite name="unit"><testcase name="test_export"/></testsuite>',
        "application/xml",
    ).run()
    app = app.text_input(key="junit_importer").set_value("QA owner").run()
    app = app.multiselect(key="junit_mapping_scopes").set_value(
        ["suite-0001"]
    ).run()
    app = app.button(key="save_junit_import").click().run()

    updated = app.session_state["review_state"]
    assert updated.bundle is not None
    assert len(updated.bundle.junit_evidence_imports) == 1
    imported = updated.bundle.junit_evidence_imports[0]
    assert imported.criterion_mappings[0].criterion_id == app.session_state[
        "selected_criterion"
    ]
    assert imported.test_cases[0].test_case_id == "suite-0001-case-0001"
    assert updated.bundle.gate == before.bundle.gate
    assert updated.bundle.resolutions == before.bundle.resolutions
    assert updated.bundle.runtime_evidence == before.bundle.runtime_evidence
    assert updated.review.final_acceptance is before.review.final_acceptance
    assert JUNIT_EVIDENCE_BOUNDARY_DESCRIPTION in [
        item.value for item in app.caption
    ]
    assert app.file_uploader(key="junit_artifact_upload_1").value is None
    assert app.text_input(key="junit_importer").value == ""
    assert app.multiselect(key="junit_mapping_scopes").value == []
    assert app.button(key="save_junit_import").disabled is True


def test_replacing_junit_upload_clears_mapping_even_when_scope_ids_match() -> None:
    app = analyzed_exact_head_standard_demo(new_app())
    app = app.file_uploader(key="junit_artifact_upload").upload(
        "first.xml",
        b'<testsuite name="first"><testcase name="one"/></testsuite>',
        "application/xml",
    ).run()
    app = app.multiselect(key="junit_mapping_scopes").set_value(
        ["suite-0001"]
    ).run()

    app = app.file_uploader(key="junit_artifact_upload").upload(
        "second.xml",
        b'<testsuite name="second"><testcase name="two"/></testsuite>',
        "application/xml",
    ).run()

    assert app.multiselect(key="junit_mapping_scopes").value == []


def test_junit_preview_and_saved_values_render_inertly_without_raw_output() -> None:
    app = analyzed_exact_head_standard_demo(new_app())
    hostile_name = "<script>alert('suite')</script>"
    raw_output = "RAW-JUNIT-OUTPUT-SENTINEL"
    xml = (
        f'<testsuite name="{hostile_name.replace("<", "&lt;").replace(">", "&gt;")}">'
        f'<testcase name="=1+1"/><system-out>{raw_output}</system-out></testsuite>'
    ).encode()

    app = app.file_uploader(key="junit_artifact_upload").upload(
        "results.xml", xml, "application/xml"
    ).run()

    assert app.exception == []
    assert hostile_name not in [item.value for item in app.markdown]
    assert raw_output not in "\n".join(
        [
            *(item.value for item in app.text),
            *(item.value for item in app.code),
            *(item.value for item in app.caption),
            *(item.value for item in app.markdown),
        ]
    )
    assert "JUnit properties and output content were discarded during import." in [
        item.value for item in app.text
    ]


def test_junit_parser_failure_leaves_review_unchanged_and_hides_artifact_text() -> None:
    app = analyzed_exact_head_standard_demo(new_app())
    before = app.session_state["review_state"].model_copy(deep=True)
    unsafe = (
        b'<!DOCTYPE testsuite [<!ENTITY secret SYSTEM "file:///PRIVATE-SENTINEL">]>'
        b'<testsuite name="x"><testcase name="&secret;"/></testsuite>'
    )

    app = app.file_uploader(key="junit_artifact_upload").upload(
        "unsafe.xml", unsafe, "application/xml"
    ).run()

    assert app.session_state["review_state"] == before
    rendered_errors = "\n".join(item.value for item in app.error)
    assert "could not be inspected" in rendered_errors
    assert "PRIVATE-SENTINEL" not in rendered_errors
    assert app.button(key="save_junit_import").disabled is True


def test_junit_import_requires_exact_head_and_explicit_mapping() -> None:
    app = analyzed_demo(new_app())
    app = app.file_uploader(key="junit_artifact_upload").upload(
        "results.xml",
        b'<testsuite name="unit"><testcase name="test_export"/></testsuite>',
        "application/xml",
    ).run()
    app = app.text_input(key="junit_importer").set_value("QA owner").run()

    assert app.button(key="save_junit_import").disabled is True
    assert "An exact 40-character reviewed head is required before import." in [
        item.value for item in app.caption
    ]


@pytest.mark.parametrize(
    ("xml", "importer", "mapping"),
    [
        (b'<testsuite name="empty"/>', "QA owner", ["suite-0001"]),
        (
            b'<testsuite name="unit"><testcase name="test_export"/></testsuite>',
            "x" * 257,
            ["suite-0001"],
        ),
    ],
)
def test_junit_import_save_stays_disabled_until_full_draft_is_valid(
    xml: bytes,
    importer: str,
    mapping: list[str],
) -> None:
    app = analyzed_exact_head_standard_demo(new_app())
    app = app.file_uploader(key="junit_artifact_upload").upload(
        "results.xml", xml, "application/xml"
    ).run()
    app = app.text_input(key="junit_importer").set_value(importer).run()
    app = app.multiselect(key="junit_mapping_scopes").set_value(mapping).run()

    assert app.button(key="save_junit_import").disabled is True


def test_junit_import_save_stays_disabled_for_already_imported_artifact() -> None:
    xml = b'<testsuite name="unit"><testcase name="test_export"/></testsuite>'
    app = analyzed_exact_head_standard_demo(new_app())
    app = app.file_uploader(key="junit_artifact_upload").upload(
        "results.xml", xml, "application/xml"
    ).run()
    app = app.text_input(key="junit_importer").set_value("QA owner").run()
    app = app.multiselect(key="junit_mapping_scopes").set_value(
        ["suite-0001"]
    ).run()
    app = app.button(key="save_junit_import").click().run()

    app = app.file_uploader(key="junit_artifact_upload_1").upload(
        "results.xml", xml, "application/xml"
    ).run()
    app = app.text_input(key="junit_importer").set_value("QA owner").run()
    app = app.multiselect(key="junit_mapping_scopes").set_value(
        ["suite-0001"]
    ).run()

    assert app.button(key="save_junit_import").disabled is True
