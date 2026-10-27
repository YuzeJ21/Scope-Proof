import csv
import io
import json

import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)


@pytest.mark.parametrize("recorded", [True, False])
def test_exports_distinguish_recorded_source_from_unknown_legacy_build(recorded: bool) -> None:
    bundle = build_demo_review()
    if not recorded:
        bundle.review.analysis_source_identity = None
    identity = bundle.review.analysis_source_identity
    expected = f"{identity.scheme}:{identity.sha256}" if identity else "Not captured"
    assert f"Analysis core source:** <code>{expected}</code>" in export_markdown(bundle)
    assert f"Analysis core source: <code>{expected}</code>" in export_html(bundle)
    row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    assert row["analysis_core_source"] == expected
    raw = json.loads(export_json(bundle))
    assert raw["review"]["analysis_source_identity"] == (
        identity.model_dump(mode="json") if identity else None
    )
    assert "validation uses the installed policy" in export_markdown(bundle)
    assert "validation uses the installed policy" in export_html(bundle)
