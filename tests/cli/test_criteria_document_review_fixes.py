"""CONSTRUCTED counterexamples from independent whole-branch review."""

import json
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from scopeproof_core.cli import main
from scopeproof_core.criteria.confirmation import build_criteria_source_provenance
from scopeproof_core.schemas.models import Criterion


@pytest.mark.parametrize("source_text", ["", " \t\r\n"])
@pytest.mark.parametrize("operation", ["prepare", "validate", "fixture", "network"])
def test_blank_original_source_fails_before_confirmation_or_ingestion(
    tmp_path, capsys, monkeypatch, source_text, operation,
):
    source = tmp_path / "blank-source.txt"
    source.write_bytes(source_text.encode())
    criteria = [Criterion(criterion_id="AC-20", text="CONSTRUCTED normalized promise")]
    document = tmp_path / "criteria.json"
    document.write_text(json.dumps({
        "schema_version": 1, "source_text_sha256": sha256(source.read_bytes()).hexdigest(),
        "criteria": [c.model_dump(mode="json") for c in criteria],
    }), encoding="utf-8")
    # A consistent external confirmation must not bypass the owning source's validity rule.
    confirmation = tmp_path / "external-confirmation.json"
    confirmation.write_text(build_criteria_source_provenance(
        source_uri="https://example.test/constructed", source_text=source_text, criteria=criteria,
        confirmed_by="CONSTRUCTED asserted role", confirmed_at=datetime(2026, 11, 2, tzinfo=UTC),
    ).model_dump_json(), encoding="utf-8")
    common = ["--requirements", str(source), "--criteria", str(document)]
    calls = []

    def forbidden_fetch(*_args, **_kwargs):
        calls.append("unexpected network ingestion")
        raise ValueError("unexpected network ingestion")

    monkeypatch.setattr("scopeproof_core.cli.GitHubClient.fetch_pull_request", forbidden_fetch)
    output = tmp_path / "must-not-write.json"
    storage = tmp_path / "reviews"
    if operation == "prepare":
        args = ["prepare-requirements-confirmation", *common,
                "--source-uri", "https://example.test/constructed", "--confirmed-by",
                "CONSTRUCTED asserted role", "--output", str(output)]
    elif operation == "validate":
        args = ["validate-requirements-confirmation", *common, "--confirmation", str(confirmation)]
    else:
        ingestion = (["--pr", "https://github.com/acme/repo/pull/7"] if operation == "network"
                     else ["--fixture", str(tmp_path / "must-not-read.json")])
        args = ["review", *common, "--confirmation", str(confirmation), *ingestion,
                "--storage-dir", str(storage), "--report", str(output)]
    with pytest.raises(SystemExit) as raised:
        main(args)
    assert raised.value.code == 2
    assert calls == []
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "requirements source must contain non-whitespace text" in captured.err
    assert "must-not-read" not in captured.err
    assert not storage.exists() and not output.exists()
