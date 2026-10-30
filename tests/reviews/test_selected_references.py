"""Exact-head reviewer references never change automatic or acceptance truth."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from importlib import import_module

import pytest
from pydantic import ValidationError

from scopeproof_core.demo import build_review, load_demo_labels, load_demo_snapshot
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.lifecycle import (
    append_resolution,
    new_review_state,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    Criterion,
    EvidenceLevel,
    EvidenceSourceScope,
    EvidenceType,
    HumanDecision,
    IngestionState,
    LineChangeType,
    ResolutionEvent,
    RetrievedFile,
    ReviewBundle,
)
from scopeproof_core.storage.json_store import JsonReviewStore


def api():
    return import_module("scopeproof_core.reviews.selected_references")


def source_state(files=None):
    snapshot = load_demo_snapshot().model_copy(deep=True)
    snapshot.files = (
        files
        if files is not None
        else [
            ChangedFile(
                path="src/export.py",
                status="modified",
                lines=[
                    ChangedLine(change_type=LineChangeType.REMOVED, line_number=9, content="old"),
                    ChangedLine(
                        change_type=LineChangeType.CONTEXT,
                        line_number=10,
                        content="  unfamiliar_symbol = 42  ",
                    ),
                    ChangedLine(
                        change_type=LineChangeType.ADDED, line_number=11, content="new_symbol()"
                    ),
                ],
            )
        ]
    )
    return new_review_state(build_review(snapshot, load_demo_labels())), snapshot


def append(state, snapshot, selected=None, **kwargs):
    module = api()
    if selected is None:
        selected = module.selectable_reference_lines(state, snapshot)[0]
    return module.append_reviewer_selected_reference(
        state,
        snapshot=snapshot,
        selected=selected,
        criterion_id=kwargs.pop("criterion_id", state.criteria_revision.criteria[0].criterion_id),
        reviewer=kwargs.pop("reviewer", "Fixture reviewer"),
        rationale=kwargs.pop("rationale", "This line supplies the explicitly identified context."),
        expected_state_fingerprint=kwargs.pop(
            "expected_state_fingerprint", JsonReviewStore.state_fingerprint(state)
        ),
        **kwargs,
    )


def test_bundle_starts_without_invented_reviewer_references():
    state, _ = source_state()
    assert "reviewer_selected_references" in type(state.bundle).model_fields
    assert state.bundle.reviewer_selected_references == []


def test_omitted_line_selection_preserves_all_automatic_and_human_truth():
    state, snapshot = source_state()
    state = append_resolution(
        state,
        ResolutionEvent(
            criterion_id=state.criteria_revision.criteria[0].criterion_id,
            decision=HumanDecision.CHANGE_REQUIRED,
            reviewer="Original reviewer",
            comment="Original decision stays authoritative.",
        ),
    )
    before = state.model_dump(mode="json")
    updated = append(state, snapshot)
    reference = updated.bundle.reviewer_selected_references[0]
    assert reference.excerpt == "  unfamiliar_symbol = 42  "
    assert reference.excerpt_sha256 == sha256(b"  unfamiliar_symbol = 42  ").hexdigest()
    assert reference.line_number == 10
    assert reference.review_id == state.review.review_id
    assert reference.head_sha == snapshot.head_sha
    assert reference.criteria_revision_number == 1
    assert reference.criteria_source_provenance == state.review.criteria_source_provenance
    assert reference.reviewer == "Fixture reviewer"
    assert reference.rationale == "This line supplies the explicitly identified context."
    assert reference.evidence_type is EvidenceType.IMPLEMENTATION
    assert reference.evidence_level is EvidenceLevel.E1
    assert reference.permalink == (
        f"https://github.com/{snapshot.repository}/blob/{snapshot.head_sha}/src/export.py#L10-L10"
    )
    assert reference.selected_at.tzinfo is not None
    after = updated.model_dump(mode="json")
    after["bundle"]["reviewer_selected_references"] = []
    assert after == before
    assert state.bundle.reviewer_selected_references == []
    assert validated_review_state(updated) == updated
    with pytest.raises(ValidationError):
        reference.reviewer = "Replacement"


def test_sources_are_numbered_sorted_and_derive_test_intent_without_execution():
    state, snapshot = source_state(
        [
            ChangedFile(
                path="tests/test_z.py",
                status="added",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED,
                        line_number=3,
                        content="def test_intent():",
                    )
                ],
            ),
            ChangedFile(
                path="src/current.py",
                previous_path="src/old.py",
                status="renamed",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.CONTEXT, line_number=2, content="current()"
                    )
                ],
            ),
            ChangedFile(
                path="generated/schema.py",
                status="modified",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED, line_number=1, content="generated = True"
                    )
                ],
            ),
            ChangedFile(
                path="docs/notes.md",
                status="added",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED, line_number=4, content="Read this note"
                    )
                ],
            ),
        ]
    )
    unchanged = [
        RetrievedFile(
            path="src/unchanged.py",
            content="first\nsecond\n",
            commit_sha=snapshot.head_sha,
            retrieval_reason="Already ingested fixture",
        )
    ]
    lines = api().selectable_reference_lines(state, snapshot, unchanged)
    assert [(line.file_path, line.line_number, line.excerpt) for line in lines] == [
        ("docs/notes.md", 4, "Read this note"),
        ("generated/schema.py", 1, "generated = True"),
        ("src/current.py", 2, "current()"),
        ("tests/test_z.py", 3, "def test_intent():"),
        ("src/unchanged.py", 1, "first"),
        ("src/unchanged.py", 2, "second"),
    ]
    test_line = lines[3]
    assert test_line.evidence_type is EvidenceType.TEST
    assert test_line.evidence_level is EvidenceLevel.E2
    assert lines[4].source_scope is EvidenceSourceScope.UNCHANGED_CANDIDATE
    updated = append(state, snapshot, test_line)
    assert updated.bundle.runtime_evidence == []
    assert updated.bundle.findings == state.bundle.findings
    assert "non-gating" in api().REVIEWER_SELECTED_REFERENCE_BOUNDARY.lower()
    assert "execution" in api().REVIEWER_SELECTED_REFERENCE_BOUNDARY.lower()
    assert (
        api().selectable_reference_lines(
            state, snapshot.model_copy(update={"files": list(reversed(snapshot.files))}), unchanged
        )
        == lines
    )
    with pytest.raises(ValidationError):
        test_line.excerpt = "Modified"


@pytest.mark.parametrize(
    "field,value",
    [
        ("repository", "other/repo"),
        ("pr_number", 999),
        ("head_sha", "other-head"),
        ("base_sha", "other-base"),
    ],
)
def test_source_identity_mismatch_is_rejected(field, value):
    state, snapshot = source_state()
    with pytest.raises(ValueError, match="match"):
        api().selectable_reference_lines(state, snapshot.model_copy(update={field: value}))


def test_source_inventory_mismatch_unknown_and_unconfirmed_are_rejected():
    state, snapshot = source_state()
    changed = snapshot.model_copy(deep=True)
    changed.files.append(ChangedFile(path="src/extra.py", status="added"))
    with pytest.raises(ValueError, match="inventory"):
        api().selectable_reference_lines(state, changed)
    unknown = state.model_copy(deep=True)
    unknown.review.changed_file_inventory = None
    unknown.bundle.review.changed_file_inventory = None
    unknown.bundle.gate = evaluate_gate(
        unknown.review,
        unknown.bundle.criteria,
        unknown.bundle.findings,
        unknown.bundle.resolutions,
        unknown.bundle.evidence,
    )
    with pytest.raises(ValueError, match="inventory"):
        api().selectable_reference_lines(unknown, snapshot)
    pending = revise_criteria(
        state, [Criterion(criterion_id="AC-01", text="New criterion")], "New criterion"
    )
    with pytest.raises(ValueError, match=r"confirmed|active"):
        api().selectable_reference_lines(pending, snapshot)


def test_unsafe_and_ambiguous_sources_never_offer_lines():
    state, snapshot = source_state(
        [
            ChangedFile(
                path="src/good.py",
                status="modified",
                lines=[
                    ChangedLine(change_type=LineChangeType.ADDED, line_number=1, content="good()")
                ],
            ),
            ChangedFile(
                path="src/deleted.py",
                status="removed",
                lines=[
                    ChangedLine(change_type=LineChangeType.CONTEXT, line_number=1, content="gone()")
                ],
            ),
            ChangedFile(
                path="src/truncated.py",
                status="modified",
                truncated=True,
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED, line_number=1, content="partial()"
                    )
                ],
            ),
            ChangedFile(
                path="src/duplicate.py",
                status="modified",
                lines=[
                    ChangedLine(change_type=LineChangeType.ADDED, line_number=3, content="one()"),
                    ChangedLine(change_type=LineChangeType.CONTEXT, line_number=3, content="two()"),
                ],
            ),
            ChangedFile(
                path="../outside.py",
                status="modified",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED, line_number=1, content="outside()"
                    )
                ],
            ),
            ChangedFile(
                path="src/blank.py",
                status="added",
                lines=[
                    ChangedLine(change_type=LineChangeType.ADDED, line_number=1, content=" \t"),
                    ChangedLine(
                        change_type=LineChangeType.ADDED, line_number=None, content="unlocated()"
                    ),
                    ChangedLine(
                        change_type=LineChangeType.ADDED, line_number=2, content="é" * 2049
                    ),
                    ChangedLine(
                        change_type=LineChangeType.ADDED, line_number=3, content="one\ntwo"
                    ),
                ],
            ),
        ]
    )
    snapshot.skipped_files = ["src/skipped.py"]
    snapshot.ingestion_state = IngestionState.PARTIAL
    state, snapshot = new_review_state(build_review(snapshot, load_demo_labels())), snapshot
    unchanged = [
        RetrievedFile(
            path="src/deleted.py",
            content="bypass",
            commit_sha=snapshot.head_sha,
            retrieval_reason="Previously loaded",
        ),
        RetrievedFile(
            path="src/skipped.py",
            content="bypass",
            commit_sha=snapshot.head_sha,
            retrieval_reason="Previously loaded",
        ),
        RetrievedFile(
            path="src/stale.py",
            content="old",
            commit_sha="old-head",
            retrieval_reason="Previously loaded",
        ),
        RetrievedFile(
            path="src/ambiguous.py",
            content="first",
            commit_sha=snapshot.head_sha,
            retrieval_reason="Previously loaded",
        ),
        RetrievedFile(
            path="src/ambiguous.py",
            content="second",
            commit_sha=snapshot.head_sha,
            retrieval_reason="Previously loaded",
        ),
    ]
    lines = api().selectable_reference_lines(state, snapshot, unchanged)
    assert [(line.file_path, line.excerpt) for line in lines] == [("src/good.py", "good()")]


def test_line_and_collection_limits_are_enforced():
    state, snapshot = source_state(
        [
            ChangedFile(
                path="src/large.py",
                status="modified",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED, line_number=index, content=f"line {index}"
                    )
                    for index in range(1, 1003)
                ],
            )
        ]
    )
    lines = api().selectable_reference_lines(state, snapshot)
    assert len(lines) == 1000
    assert lines[-1].line_number == 1000
    for selected in lines[:32]:
        state = append(state, snapshot, selected)
    with pytest.raises(ValueError, match=r"32|limit"):
        append(state, snapshot, lines[32])
    assert len(state.bundle.reviewer_selected_references) == 32


@pytest.mark.parametrize(
    "change",
    [
        {"excerpt": "Invented source"},
        {"line_number": 100},
        {"file_path": "src/missing.py"},
        {"evidence_type": EvidenceType.TEST, "evidence_level": EvidenceLevel.E2},
        {"source_scope": EvidenceSourceScope.UNCHANGED_CANDIDATE},
    ],
)
def test_spoofed_selected_values_are_rejected(change):
    state, snapshot = source_state()
    selected = api().selectable_reference_lines(state, snapshot)[0]
    with pytest.raises(ValueError, match=r"source|selectable"):
        append(state, snapshot, selected.model_copy(update=change))
    assert state.bundle.reviewer_selected_references == []


def test_duplicate_invalid_mapping_blank_attribution_and_stale_state_are_rejected():
    state, snapshot = source_state()
    selected = api().selectable_reference_lines(state, snapshot)[0]
    fingerprint = JsonReviewStore.state_fingerprint(state)
    updated = append(state, snapshot, selected)
    with pytest.raises(ValueError, match="already exists"):
        append(updated, snapshot, selected)
    for kwargs in [
        {"criterion_id": "missing"},
        {"reviewer": "  "},
        {"rationale": "\t"},
        {"reviewer": "a" * 201},
        {"rationale": "x" * 2001},
    ]:
        with pytest.raises(ValueError):
            append(state, snapshot, selected, **kwargs)
    with pytest.raises(ValueError, match="stale"):
        append(updated, snapshot, selected, expected_state_fingerprint=fingerprint)
    changed_source = snapshot.model_copy(deep=True)
    changed_source.files[0].lines[1].content = "Different source at same location"
    with pytest.raises(ValueError, match=r"source|selectable"):
        append(state, changed_source, selected)


def test_append_unchanged_reference_and_preserve_it_only_in_prior_revision():
    state, snapshot = source_state()
    unchanged = [
        RetrievedFile(
            path="src/helper.py",
            content="helper()",
            commit_sha=snapshot.head_sha,
            retrieval_reason="Already ingested",
        )
    ]
    selected = api().selectable_reference_lines(state, snapshot, unchanged)[-1]
    updated = append(state, snapshot, selected, unchanged_files=unchanged)
    reference = updated.bundle.reviewer_selected_references[0]
    assert reference.source_scope is EvidenceSourceScope.UNCHANGED_CANDIDATE
    assert reference.line_number == 1
    revised = revise_criteria(
        updated, [Criterion(criterion_id="AC-01", text="New criterion")], "New criterion"
    )
    assert revised.bundle is None
    assert revised.analysis_history[-1].reviewer_selected_references == [reference]
    assert validated_review_state(revised) == revised


@pytest.mark.parametrize(
    "field,value",
    [
        ("excerpt_sha256", "0" * 64),
        ("evidence_level", EvidenceLevel.E4),
        ("permalink", "https://github.com/other/repo/blob/head/file#L1"),
        ("line_number", 0),
        ("line_number", True),
        ("file_path", "../file"),
        ("excerpt", "a\nb"),
        ("selected_at", datetime(2026, 10, 30)),
    ],
)
def test_reference_schema_rejects_invalid_source_contract(field, value):
    state, snapshot = source_state()
    reference = append(state, snapshot).bundle.reviewer_selected_references[0]
    with pytest.raises(ValueError):
        type(reference).model_validate({**reference.model_dump(), field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("review_id", "other"),
        ("repository", "other/repo"),
        ("pr_number", 987),
        ("head_sha", "other-head"),
        ("criteria_revision_number", 2),
        ("confirmed_criteria_sha256", "0" * 64),
        ("criterion_id", "missing"),
        ("criteria_source_provenance", None),
    ],
)
def test_bundle_rejects_reference_outside_owning_confirmed_analysis(field, value):
    state, snapshot = source_state()
    updated = append(state, snapshot)
    payload = updated.bundle.model_dump(mode="python")
    payload["reviewer_selected_references"][0][field] = value
    with pytest.raises(ValueError):
        ReviewBundle.model_validate(payload)


def test_bundle_rejects_duplicate_reference_ids_and_duplicate_criterion_locations():
    state, snapshot = source_state()
    updated = append(state, snapshot)
    original = updated.bundle.reviewer_selected_references[0]
    for duplicate in [original, original.model_copy(update={"reference_id": "another"})]:
        payload = updated.bundle.model_dump(mode="python")
        payload["reviewer_selected_references"].append(duplicate.model_dump())
        with pytest.raises(ValueError, match=r"unique|duplicate"):
            ReviewBundle.model_validate(payload)


def test_reference_limit_schema_rejects_excess_records():
    state, snapshot = source_state()
    updated = append(state, snapshot)
    payload = updated.bundle.model_dump(mode="python")
    payload["reviewer_selected_references"] *= 33
    with pytest.raises(ValueError):
        ReviewBundle.model_validate(payload)


def test_mutated_state_and_source_are_revalidated_at_core_boundary():
    state, snapshot = source_state()
    selected = api().selectable_reference_lines(state, snapshot)[0]
    state.bundle.findings[0].reason = "  "
    with pytest.raises(ValueError):
        append(state, snapshot, selected)
    state, snapshot = source_state()
    snapshot.files[0].lines[1].line_number = 0
    with pytest.raises(ValueError):
        api().selectable_reference_lines(state, snapshot)


def test_final_acceptance_is_rejected_before_reference_mutation():
    state = new_review_state(build_review(load_demo_snapshot(), load_demo_labels()))
    snapshot = load_demo_snapshot()
    for criterion in state.criteria_revision.criteria:
        state = append_resolution(
            state,
            ResolutionEvent(
                criterion_id=criterion.criterion_id,
                decision=HumanDecision.ACCEPTED,
                comment="Fixture reviewer accepts below-level evidence with rationale.",
            ),
        )
    from scopeproof_core.reviews.lifecycle import append_file_scope_decision
    from scopeproof_core.schemas.models import FileScopeDecision

    for path in state.review.changed_file_inventory.files:
        state = append_file_scope_decision(
            state,
            FileScopeDecision(
                review_id=state.review.review_id,
                path=path.path,
                head_sha=state.review.head_sha,
                criteria_revision_number=1,
                normalized_criteria_sha256=state.review.criteria_source_provenance.normalized_criteria_sha256,
                disposition="outside_confirmed_criteria",
                reviewer="Fixture reviewer",
                note="Constructed file scope disposition",
            ),
        )
    state = append_resolution(state, ResolutionEvent(final_acceptance=True))
    with pytest.raises(ValueError, match="final acceptance"):
        append(state, snapshot)


def test_live_reference_permalink_and_full_sha_are_exactly_bound():
    state, snapshot = source_state()
    from scopeproof_core.schemas.models import RepositoryVisibility, ReviewInputOrigin

    snapshot.head_sha = "a" * 40
    snapshot.base_sha = "b" * 40
    snapshot.repository_visibility = RepositoryVisibility.VERIFIED_PUBLIC
    bundle = build_review(snapshot, load_demo_labels())
    bundle.review.input_origin = ReviewInputOrigin.LIVE_PUBLIC_GITHUB
    bundle.review.repository_visibility = RepositoryVisibility.VERIFIED_PUBLIC
    state = new_review_state(bundle)
    reference = append(state, snapshot).bundle.reviewer_selected_references[0]
    assert reference.head_sha == "a" * 40
    assert f"/blob/{'a' * 40}/" in reference.permalink


def test_persisted_unchanged_reference_cannot_relabel_a_renamed_previous_path():
    state, snapshot = source_state(
        [
            ChangedFile(
                path="src/current.py",
                previous_path="src/old.py",
                status="renamed",
                lines=[
                    ChangedLine(change_type=LineChangeType.ADDED, line_number=1, content="new()")
                ],
            )
        ]
    )
    updated = append(state, snapshot)
    payload = updated.bundle.model_dump(mode="python")
    reference = payload["reviewer_selected_references"][0]
    reference["source_scope"] = EvidenceSourceScope.UNCHANGED_CANDIDATE
    reference["file_path"] = "src/old.py"
    reference["permalink"] = (
        f"https://github.com/{snapshot.repository}/blob/{snapshot.head_sha}/src/old.py#L1-L1"
    )
    with pytest.raises(ValueError, match=r"changed|previous"):
        ReviewBundle.model_validate(payload)
