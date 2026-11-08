"""The first-use HTML sample is constructed, byte-bound and usable without ScopeProof."""

import json
import zipfile
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs/examples/offline-handoff"
REPORT = EXAMPLE / "constructed-v026-review.html"


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.resources = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        attributes = dict(attrs)
        if "src" in attributes or tag == "link":
            self.resources.append(attributes)


def _manifest():
    from scripts.build_offline_handoff_sample import SampleManifest

    return SampleManifest.model_validate_json((EXAMPLE / "provenance.json").read_bytes())


def test_evaluator_can_download_a_labelled_self_contained_report():
    assert REPORT.is_file(), "A real offline report must be available before installation"
    from scripts.build_offline_handoff_sample import SAMPLE_DISCLOSURE

    rendered = REPORT.read_text(encoding="utf-8")
    assert rendered.index(SAMPLE_DISCLOSURE) < rendered.index("<h1>")
    assert "CONSTRUCTED EXAMPLE — NOT A REAL REVIEW" in SAMPLE_DISCLOSURE
    assert "synthetic" in SAMPLE_DISCLOSURE and "do not resolve" in SAMPLE_DISCLOSURE
    assert "no actual target runtime or human use" in SAMPLE_DISCLOSURE
    assert "<strong>Review status:</strong> Action required" in rendered
    assert "<strong>Recorded final acceptance:</strong> No" in rendered
    assert "Criteria revision 2" in rendered
    assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in rendered
    assert "<h2>Review Status Reasons</h2>" in rendered and "blocking_criteria" in rendered
    assert "<h2>What To Do Next</h2>" in rendered
    assert "AC-03" in rendered and "Resolution" in rendered
    assert "constructed-active-manual" in rendered
    assert "Constructed automation only; no actual target runtime or human use." in rendered
    parser = ReportParser()
    parser.feed(rendered)
    assert not {"script", "iframe", "form", "object", "embed"}.intersection(parser.tags)
    assert parser.resources == []


def test_sample_manifest_binds_input_recipe_and_unmodified_export_body():
    from scripts.build_offline_handoff_sample import SAMPLE_DISCLOSURE

    manifest = _manifest()
    report = REPORT.read_bytes()
    assert manifest.presented_report.name == REPORT.name
    assert manifest.presented_report.bytes == len(report)
    assert manifest.presented_report.sha256 == sha256(report).hexdigest()
    for artifact in (manifest.input_record, manifest.recipe):
        raw = (ROOT / artifact.name).read_bytes()
        assert artifact.bytes == len(raw) and artifact.sha256 == sha256(raw).hexdigest()
    raw_report = report.decode("utf-8").replace(SAMPLE_DISCLOSURE, "", 1).encode("utf-8")
    assert manifest.exported_html.bytes == len(raw_report)
    assert manifest.exported_html.sha256 == sha256(raw_report).hexdigest()
    assert report.count(SAMPLE_DISCLOSURE.encode("utf-8")) == 1
    assert manifest.package_version == "0.2.6"
    assert manifest.criteria_revision_number == 2
    assert manifest.active_gate == "blocked"
    assert manifest.actual_target_runtime is manifest.human_use is False


def test_sample_download_archive_contains_only_the_labelled_html():
    archive = EXAMPLE / "constructed-v026-review.zip"
    assert archive.is_file(), "GitHub's binary download must open as an extractable sample"
    manifest = _manifest()
    raw = archive.read_bytes()
    assert manifest.download_archive.name == archive.name
    assert manifest.download_archive.bytes == len(raw)
    assert manifest.download_archive.sha256 == sha256(raw).hexdigest()
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.namelist() == [REPORT.name]
        assert zipped.testzip() is None
        assert zipped.read(REPORT.name) == REPORT.read_bytes()
        assert zipped.getinfo(REPORT.name).date_time == (1980, 1, 1, 0, 0, 0)


@pytest.mark.parametrize(
    "field,value",
    [
        ("package_version", "0.2.7.dev0"),
        ("criteria_revision_number", 2.0),
        ("active_gate", "ready"),
        ("recorded_final_acceptance", True),
        ("actual_target_runtime", 0),
        ("human_use", True),
        ("unexpected", "ignored"),
    ],
)
def test_sample_manifest_rejects_wrong_identity_or_evidence_credit(field, value):
    from scripts.build_offline_handoff_sample import SampleManifest

    payload = json.loads((EXAMPLE / "provenance.json").read_bytes())
    payload[field] = value
    with pytest.raises(ValidationError):
        SampleManifest.model_validate(payload)


def test_sample_presentation_transform_changes_only_one_disclosure():
    from scripts.build_offline_handoff_sample import SAMPLE_DISCLOSURE, label_sample_report

    raw = "<!doctype html><html><body><h1>Example</h1></body></html>"
    labelled = label_sample_report(raw)
    assert labelled == raw.replace("<body>", "<body>" + SAMPLE_DISCLOSURE)
    assert labelled.replace(SAMPLE_DISCLOSURE, "", 1) == raw
    for invalid in ("missing body", raw + "<body>", labelled):
        with pytest.raises(ValueError):
            label_sample_report(invalid)


def test_sample_entry_precedes_installation_and_links_the_download():
    guide = (ROOT / "docs/evaluation-guide.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert guide.index("Inspect a report without installing") < guide.index(
        "Run the released source"
    )
    download = (
        "https://github.com/YuzeJ21/Scope-Proof/raw/refs/heads/main/"
        "docs/examples/offline-handoff/constructed-v026-review.zip"
    )
    assert download in guide and download in readme
    assert "synthetic" in guide and "not an importable saved record" in guide
