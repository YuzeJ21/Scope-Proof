"""Revision labels describe the selected analysis, without promoting pending state.

Native records and the demo are constructed automation, not target-runtime or human use.
"""

import csv
import io
import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.schemas.models import ReviewBundle, ReviewState
from tests.storage.test_released_v026_upgrade import CORE_SHA256, _native_store

Renderer = Callable[[ReviewBundle | ReviewState], str]
RENDERERS = [pytest.param(export_csv, id="csv"), pytest.param(export_html, id="html")]
ANALYSIS_ONLY_BOUNDARY = "Full resolution history is unavailable for this analysis-only report."


def _assert_revision(render: Renderer, value: ReviewBundle | ReviewState, expected: str) -> str:
    rendered = render(value)
    if render is export_csv:
        rows = list(csv.DictReader(io.StringIO(rendered)))
        assert rows
        assert {row["criteria_revision"] for row in rows} == {expected}
    else:
        label = re.search(r"\bCriteria revision ([^<]+)</p>", rendered)
        assert label is not None
        assert label.group(1) == expected
    return rendered


@pytest.mark.parametrize("render", RENDERERS)
def test_retained_native_revision_is_not_replaced_by_first_or_pending_revision(
    tmp_path: Path,
    render: Renderer,
) -> None:
    store, copied, original, record = _native_store(tmp_path, "pending-rich")
    state = store.load(record.review_id)
    before = state.model_dump(mode="json")
    selected = state.analysis_history[1]
    assert state.criteria_revision.number == 3
    assert state.bundle is None and not state.criteria_revision.confirmed
    assert selected.criteria_revision_number == 2

    rendered = _assert_revision(render, selected, "2")

    assert selected.review.tool_version == "0.2.6"
    assert selected.review.analysis_source_identity is not None
    assert selected.review.analysis_source_identity.sha256 == CORE_SHA256
    assert "0.2.6" in rendered and CORE_SHA256 in rendered
    if render is export_html:
        assert ANALYSIS_ONLY_BOUNDARY in rendered
        assert "Active criteria revision:" not in rendered
    # JSON remains the exact selected analysis, rather than a fabricated current state.
    assert json.loads(export_json(selected)) == before["analysis_history"][1]
    assert state.model_dump(mode="json") == before
    assert copied.read_bytes() == original


@pytest.mark.parametrize("render", RENDERERS)
def test_bare_legacy_default_revision_stays_unknown(render: Renderer) -> None:
    # The supported schema default is unknown; no revision-bound audit records are invented.
    bundle = build_demo_review()
    assert bundle.criteria_revision_number == "unknown"
    before = bundle.model_dump(mode="json")

    rendered = _assert_revision(render, bundle, "unknown")

    if render is export_html:
        assert ANALYSIS_ONLY_BOUNDARY in rendered
    assert json.loads(export_json(bundle))["criteria_revision_number"] == "unknown"
    assert bundle.model_dump(mode="json") == before


@pytest.mark.parametrize("render", RENDERERS)
def test_explicit_native_first_revision_remains_first(tmp_path: Path, render: Renderer) -> None:
    store, copied, original, record = _native_store(tmp_path, "pending-rich")
    state = store.load(record.review_id)
    selected = state.analysis_history[0]
    assert selected.criteria_revision_number == 1
    before = state.model_dump(mode="json")

    rendered = _assert_revision(render, selected, "1")

    if render is export_html:
        assert ANALYSIS_ONLY_BOUNDARY in rendered
    assert state.model_dump(mode="json") == before
    assert copied.read_bytes() == original


@pytest.mark.parametrize("render", RENDERERS)
def test_complete_native_state_keeps_current_revision_and_history(
    tmp_path: Path,
    render: Renderer,
) -> None:
    store, copied, original, record = _native_store(tmp_path, "active-rich")
    state = store.load(record.review_id)
    assert state.bundle is not None
    assert state.criteria_revision.number == state.bundle.criteria_revision_number == 2
    before = state.model_dump(mode="json")

    rendered = _assert_revision(render, state, "2")

    if render is export_html:
        assert "Active criteria revision: 2" in rendered
        assert ANALYSIS_ONLY_BOUNDARY not in rendered
    assert state.model_dump(mode="json") == before
    assert copied.read_bytes() == original


@pytest.mark.parametrize("render", [export_csv, export_html, export_json, export_markdown])
def test_pending_current_state_still_cannot_export(tmp_path: Path, render: Renderer) -> None:
    store, copied, original, record = _native_store(tmp_path, "pending-rich")
    state = store.load(record.review_id)
    before = state.model_dump(mode="json")

    with pytest.raises(ValueError, match=r"criteria source provenance|confirmed analysis"):
        render(state)

    assert state.model_dump(mode="json") == before
    assert copied.read_bytes() == original
