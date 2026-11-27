"""The maintained walkthrough reuses the private candidate without upgrading its evidence."""

import json
import shutil
import zipfile
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.build_ci_walkthrough import (
    DISCLOSURE,
    DownloadReceipt,
    WalkthroughManifest,
    build_walkthrough,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/examples/ci-handoff/source"


def _files(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_walkthrough_preserves_originals_and_explains_three_exact_build_states(tmp_path):
    before = _files(SOURCE)
    output = tmp_path / "walkthrough"
    manifest = build_walkthrough(SOURCE, output)
    assert _files(SOURCE) == before
    assert [step.label for step in manifest.steps] == ["A", "B", "B-targeted"]
    a, b, targeted = manifest.steps
    assert a.head_sha != b.head_sha == targeted.head_sha
    assert b.review_sha256 == targeted.review_sha256
    assert [list(step.outcomes.values()) for step in manifest.steps] == [
        ["Passed", "Passed", "Passed"],
        ["Failed", "Explicitly skipped", "Passed"],
        ["Failed", "Failed", "Passed"],
    ]
    assert all(step.gate == "blocked" and not step.final_acceptance for step in manifest.steps)
    index = (output / "index.html").read_text(encoding="utf-8")
    assert "What changed" in index and "What to check next" in index
    assert "same Build B commit" in index and "does not fix" in index
    assert "AC-01" in index and "AC-02" in index
    assert DISCLOSURE in index
    for step in manifest.steps:
        report = (output / step.report).read_bytes()
        assert report.count(DISCLOSURE.encode()) == 1
        raw = report.replace(DISCLOSURE.encode(), b"", 1)
        assert sha256(raw).hexdigest() == step.original_report_sha256
        assert raw == (SOURCE / f"{step.report}.txt").read_bytes()
        assert step.manifest_sha256 in report.decode() and step.head_sha in report.decode()
    for artifact in manifest.artifacts:
        payload = (output / artifact.name).read_bytes()
        assert (len(payload), sha256(payload).hexdigest()) == (artifact.bytes, artifact.sha256)
    decoded = WalkthroughManifest.model_validate_json((output / "provenance.json").read_bytes())
    assert decoded == manifest


def test_identical_inputs_produce_identical_reports_provenance_and_zip(tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    build_walkthrough(SOURCE, one)
    build_walkthrough(SOURCE, two)
    assert _files(one) == _files(two)
    with zipfile.ZipFile(one / "constructed-ci-walkthrough.zip") as archive:
        assert "index.html" in archive.namelist() and "provenance.json" in archive.namelist()
        assert archive.testzip() is None
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
        assert not any(name.endswith((".py", ".html.txt")) for name in archive.namelist())
    receipt = DownloadReceipt.model_validate_json((one / "download.json").read_bytes())
    for artifact in (receipt.archive, receipt.provenance):
        payload = (one / artifact.name).read_bytes()
        assert artifact.sha256 == sha256(payload).hexdigest()
        assert artifact.bytes == len(payload)


def test_existing_output_is_never_replaced(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    (output / "index.html").write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        build_walkthrough(SOURCE, output)
    assert (output / "index.html").read_bytes() == b"keep"
    assert list(output.iterdir()) == [output / "index.html"]


@pytest.mark.parametrize("changed", ["report", "manifest", "raw_ci", "review", "producer"])
def test_changed_original_is_refused_before_output(tmp_path, changed):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    if changed == "report":
        path = source / "build-a.html.txt"
    elif changed == "manifest":
        path = source / "inputs/B-targeted-scopeproof-manifest.json"
    elif changed == "raw_ci":
        path = source / "inputs/B-targeted-ci.json"
    elif changed == "review":
        path = source / "inputs/B-review.json"
    else:
        path = source / "original-provenance.json"
    path.write_bytes(path.read_bytes() + b" ")
    output = tmp_path / "output"
    with pytest.raises(ValueError):
        build_walkthrough(source, output)
    assert not output.exists()


@pytest.mark.parametrize("field,value", [("human_use", True), ("human_use", 0),
                                         ("target_runtime_verified", True)])
def test_provenance_rejects_false_evidence_credit(tmp_path, field, value):
    manifest = build_walkthrough(SOURCE, tmp_path / "output")
    data = manifest.model_dump(mode="python")
    data[field] = value
    with pytest.raises(ValidationError):
        WalkthroughManifest.model_validate(data)


def test_committed_example_matches_the_reproducible_recipe(tmp_path):
    output = tmp_path / "output"
    build_walkthrough(SOURCE, output)
    example = SOURCE.parent / "reader"
    assert _files(output) == _files(example)
    original = json.loads((SOURCE / "original-provenance.json").read_bytes())
    assert original["source_commit"] == "f8be51021bb95c596802426ef05c15fabf393975"
    assert original["tool_version"] == "0.2.9.dev0"


def test_every_presented_page_is_labelled_and_uses_no_remote_resources(tmp_path):
    from tests.test_offline_handoff_sample import ReportParser

    output = tmp_path / "output"
    build_walkthrough(SOURCE, output)
    for path in output.glob("*.html"):
        text = path.read_text(encoding="utf-8")
        parser = ReportParser()
        parser.feed(text)
        assert DISCLOSURE in text
        assert not {"script", "iframe", "form", "object", "embed"}.intersection(parser.tags)
        assert parser.resources == []
        assert "@import" not in text.lower() and "url(" not in text.lower()


def test_targeted_run_distinguishes_new_execution_from_retained_build_results(tmp_path):
    output = tmp_path / "output"
    manifest = build_walkthrough(SOURCE, output)
    targeted = manifest.steps[2]
    assert targeted.executed_tests == ("row_entitlement",)
    assert targeted.result_runs == {
        "category_filter": ("B",),
        "row_entitlement": ("B-targeted",),
        "csv_header": ("B",),
    }
    index = (output / "index.html").read_text(encoding="utf-8")
    assert "Effective CI status" in index
    assert "Result supplied by run" in index
    assert "Only row_entitlement was executed in this targeted run" in index


def test_hash_bound_files_disable_checkout_newline_conversion():
    import subprocess

    files = [
        "scripts/build_ci_walkthrough.py",
        *[p.relative_to(ROOT).as_posix() for p in SOURCE.rglob("*") if p.is_file()],
        *[p.relative_to(ROOT).as_posix() for p in (SOURCE.parent / "reader").rglob("*")
          if p.is_file()],
    ]
    result = subprocess.run(
        ["git", "check-attr", "text", "--", *files], cwd=ROOT,
        capture_output=True, text=True, check=True,
    )
    assert len(result.stdout.splitlines()) == len(files)
    assert all(line.endswith(": text: unset") for line in result.stdout.splitlines())


@pytest.mark.browser
def test_walkthrough_reads_offline_at_desktop_and_phone_widths(tmp_path, request):
    if "browser" not in request.config.option.markexpr:
        pytest.skip("run explicitly with -m browser after installing Chromium")
    from playwright.sync_api import expect, sync_playwright

    output = tmp_path / "output"
    build_walkthrough(SOURCE, output)
    requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for width, height in ((1280, 800), (390, 844)):
                context = browser.new_context(viewport={"width": width, "height": height})
                context.set_offline(True)
                page = context.new_page()
                page.on("request", lambda event: requests.append(event.url)
                        if event.url.startswith(("http:", "https:")) else None)
                for path in sorted(output.glob("*.html")):
                    page.goto(path.as_uri())
                    expect(page.get_by_role("complementary", name="Constructed example"))\
                        .to_be_visible()
                    assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
                    for link in page.get_by_role("link").all():
                        href = link.get_attribute("href")
                        if not href.startswith(("https:", "#")):
                            assert (output / href).is_file(), href
                    if width == 390:
                        for table in page.locator(".table-scroll").all():
                            if table.evaluate("node => node.scrollWidth > node.clientWidth"):
                                table.focus()
                                table.press("ArrowRight")
                                page.wait_for_function(
                                    "node => node.scrollLeft > 0", arg=table.element_handle(),
                                )
                    page.screenshot(path=tmp_path / f"{path.stem}-{width}.png", full_page=True)
                context.close()
        finally:
            browser.close()
    assert requests == []
