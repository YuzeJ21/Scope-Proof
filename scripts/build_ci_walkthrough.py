"""Package the existing constructed candidate reports; never rebuild its reviews or tests."""

from __future__ import annotations

import argparse
import io
from hashlib import sha256
from html import escape
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scopeproof_core.presentation import review_status_label
from scopeproof_core.reviews.ci_status import (
    CI_STATUS_LABELS,
    criterion_ci_statuses,
    load_ci_status_manifest,
)
from scopeproof_core.storage.atomic_files import MAX_SAVED_RECORD_BYTES, read_text_no_follow
from scopeproof_core.storage.json_store import JsonReviewStore
from scripts.simulate_ci_manifest import SimulatedRun

_DIGEST = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
_COMMIT = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
_ORIGINAL_PROOF = "128e2fa3c6358c513624ec4f3a20a640a3411f65052930cb6268a5e51140a6c7"
_ARCHIVE = "constructed-ci-walkthrough.zip"
DISCLOSURE = (
    '<aside aria-label="Constructed example" style="border:2px solid #9a4b0a;'
    'padding:1rem;margin-bottom:1.5rem"><strong>CONSTRUCTED EXAMPLE</strong>'
    '<p>These are synthetic builds and fixture checks, not a real pull-request review. '
    'Ticket, actor and CI links are illustrative. No target-runtime verification, human '
    'acceptance or customer use is established. This example uses unpublished '
    'ScopeProof 0.2.9.dev0; the public evaluation release remains v0.2.8.</p></aside>'
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Artifact(StrictModel):
    name: str
    bytes: int = Field(gt=0)
    sha256: _DIGEST

    @field_validator("name")
    @classmethod
    def require_relative_name(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
            raise ValueError("artifact name must be a relative path")
        return value


class OriginalReport(StrictModel):
    case: Literal["A", "B", "B-targeted"]
    report: str
    report_sha256: _DIGEST
    review_id: str
    reviewed_head_sha: _COMMIT
    review_record_version: int
    review_record_sha256: _DIGEST
    confirmed_criteria_sha256: _DIGEST
    manifest_name: str
    manifest_sha256: _DIGEST
    raw_ci_sha256: _DIGEST
    outcomes: dict[str, str]


class OriginalProducer(StrictModel):
    kind: str
    source_commit: _COMMIT
    source_tree: _COMMIT
    tool_version: str
    python_version: str
    wheel_name: str
    wheel_sha256: _DIGEST
    wheel_payload_files_matched: int = Field(gt=0)
    simulator_sha256: _DIGEST
    inputs_unchanged: bool
    reports: list[OriginalReport]


class WalkthroughStep(StrictModel):
    label: Literal["A", "B", "B-targeted"]
    head_sha: _COMMIT
    report: str
    original_report_sha256: _DIGEST
    review_sha256: _DIGEST
    manifest_sha256: _DIGEST
    outcomes: dict[str, str]
    result_runs: dict[str, tuple[str, ...]]
    executed_tests: tuple[str, ...]
    gate: Literal["blocked"]
    review_status: Literal["Action required"]
    final_acceptance: bool


class WalkthroughManifest(StrictModel):
    schema_version: Literal["scopeproof-ci-walkthrough-v1"]
    boundary: Literal["Constructed example; no target runtime, human acceptance or customer use."]
    original_producer: OriginalProducer
    original_provenance_sha256: _DIGEST
    presentation_recipe: Artifact
    steps: tuple[WalkthroughStep, ...]
    artifacts: tuple[Artifact, ...]
    human_use: bool
    target_runtime_verified: bool

    @model_validator(mode="after")
    def preserve_evidence_boundary(self) -> WalkthroughManifest:
        if (
            self.human_use or self.target_runtime_verified
            or any(s.final_acceptance for s in self.steps)
        ):
            raise ValueError("constructed reports cannot establish runtime or human acceptance")
        if [step.label for step in self.steps] != ["A", "B", "B-targeted"]:
            raise ValueError("requires the three original scenario moments")
        a, b, targeted = self.steps
        if not (a.head_sha != b.head_sha == targeted.head_sha):
            raise ValueError("the targeted run must retain the same Build B commit")
        if b.review_sha256 != targeted.review_sha256:
            raise ValueError("the targeted run must preserve the saved review")
        if len({item.name for item in self.artifacts}) != len(self.artifacts):
            raise ValueError("duplicate output artifact")
        return self


class DownloadReceipt(StrictModel):
    archive: Artifact
    provenance: Artifact


def _artifact(name: str, payload: bytes) -> Artifact:
    return Artifact(name=name, bytes=len(payload), sha256=sha256(payload).hexdigest())


def _read(path: Path, expected: str) -> bytes:
    raw = read_text_no_follow(
        path, preserve_newlines=True, max_bytes=MAX_SAVED_RECORD_BYTES,
    ).encode("utf-8")
    if sha256(raw).hexdigest() != expected:
        raise ValueError(f"original artifact changed: {path.name}")
    return raw


def _label_report(raw: bytes) -> bytes:
    if raw.count(b"<body>") != 1 or DISCLOSURE.encode() in raw:
        raise ValueError("requires one original, unlabelled snapshot body")
    return raw.replace(b"<body>", b"<body>" + DISCLOSURE.encode(), 1)


def _index(steps: tuple[WalkthroughStep, ...], producer: OriginalProducer) -> bytes:
    actions = (
        "All mapped checks passed. Inspect the saved review's evidence gaps and file scope; "
        "required external verification and reviewer decisions are still absent.",
        "Review the AC-01 category_filter failure. Run AC-02 row_entitlement on this exact "
        "commit; an explicit skip leaves that check unresolved.",
        "Review the AC-01 category_filter and AC-02 row_entitlement failures. The targeted "
        "rerun adds a result on the same Build B commit; it does not fix the implementation.",
    )
    cards = []
    for step, title, action in zip(
        steps, ("Build A · Baseline", "Build B · Initial run", "Build B · Targeted rerun"),
        actions, strict=True,
    ):
        rows = "".join(
            f"<tr><th scope='row'>{escape(test)}</th><td>{escape(status)}</td>"
            f"<td>{escape(', '.join(step.result_runs[test]))}</td></tr>"
            for test, status in step.outcomes.items()
        )
        build = "A" if step.label == "A" else "B"
        execution = (
            "Only row_entitlement was executed in this targeted run. The filter failure "
            "and header pass are retained results from the initial B run."
            if step.label == "B-targeted"
            else "Latest run executed: " + ", ".join(step.executed_tests) + "."
        )
        cards.append(
            f"<section><h2>{title}</h2><p>Reviewed commit <code>{step.head_sha}</code></p>"
            f"<table><caption>Effective CI status · {title}</caption>"
            "<thead><tr><th scope='col'>Expected test</th><th scope='col'>Status</th>"
            f"<th scope='col'>Result supplied by run</th></tr></thead><tbody>{rows}</tbody></table>"
            f"<p>{execution}</p>"
            f"<h3>What to check next</h3><p>{action}</p>"
            f"<p>Recorded review status: <strong>{step.review_status}</strong>. "
            "Final acceptance: <strong>No</strong>.</p>"
            f"<p><a href='{step.report}'>Inspect exact-build CI snapshot</a> · "
            f"<a href='inputs/{step.label}-scopeproof-manifest.json'>Supplied CI manifest</a> · "
            f"<a href='inputs/{build}-review.json'>Unchanged saved review JSON</a></p></section>"
        )
    html = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>ScopeProof · Two-build CI handoff</title><style>"
        "*{box-sizing:border-box}body{font:1rem/1.6 system-ui,sans-serif;color:#172b3a;"
        "background:#f4f7fa;margin:0;overflow-wrap:anywhere}main{max-width:66rem;"
        "margin:auto;padding:clamp(1rem,4vw,3rem)}h1{line-height:1.15;font-size:"
        "clamp(2rem,5vw,3rem)}section{background:white;border:1px solid #bccbd5;"
        "border-radius:.6rem;padding:1.25rem;margin:1.5rem 0}table{width:100%;"
        "border-collapse:collapse}caption{text-align:left;font-weight:600}td,th{"
        "padding:.5rem;border-bottom:1px solid #bccbd5;text-align:left}"
        "a{color:#12516c}a:focus-visible{outline:3px solid #ad4d0a;outline-offset:3px}"
        "code{overflow-wrap:anywhere}footer{border-top:1px solid #bccbd5;padding-top:1rem}"
        "</style></head><body><main>" + DISCLOSURE +
        "<h1>What changed, and what still needs checking?</h1>"
        "<p>Read the three moments in order. Each snapshot cites the exact reviewed commit "
        "and supplied CI manifest. The saved acceptance review stays separate.</p>"
        "<h2>What changed</h2><p>A new build introduces a category-filter failure and leaves "
        "row access explicitly skipped. A targeted rerun then reports row access failed "
        "on the same Build B commit. The filter failure and header pass remain reported.</p>"
        + "".join(cards) +
        "<footer><h2>Producer and limits</h2><p>The original reports came from ScopeProof "
        f"<strong>{escape(producer.tool_version)}</strong>, source "
        f"<code>{producer.source_commit}</code>. "
        "This presentation adds one constructed-example disclosure to each original report. "
        "Removing that exact disclosure recovers its original bytes. ScopeProof does not "
        "authenticate the manifests. CI links use reserved example URLs.</p>"
        "<p><a href='provenance.json'>Presentation and input provenance</a> · "
        "<a href='original-provenance.json'>Original candidate provenance</a></p>"
        "</footer></main></body></html>"
    )
    return html.encode("utf-8")


def build_walkthrough(source: Path, output: Path) -> WalkthroughManifest:
    """Validate and present frozen candidate bytes in a new directory."""
    if output.exists() or output.is_symlink():
        raise FileExistsError("walkthrough output must be a new directory")
    original = _read(source / "original-provenance.json", _ORIGINAL_PROOF)
    producer = OriginalProducer.model_validate_json(original)
    files = {"original-provenance.json": original}
    steps = []
    for report in producer.reports:
        build = "A" if report.case == "A" else "B"
        raw = _read(source / f"{report.report}.txt", report.report_sha256)
        manifest_name = f"inputs/{report.manifest_name}"
        manifest_raw = _read(source / manifest_name, report.manifest_sha256)
        run_name = f"inputs/{report.case}-ci.json"
        run_raw = _read(source / run_name, report.raw_ci_sha256)
        record_name = f"inputs/{build}-review.json"
        record_raw = _read(source / record_name, report.review_record_sha256)
        state = JsonReviewStore.decode_record(record_raw.decode(), require_recorded_facts=True)
        external = load_ci_status_manifest(manifest_raw)
        run = SimulatedRun.model_validate_json(run_raw)
        if state.bundle is None or not state.criteria_revision.confirmed:
            raise ValueError("walkthrough requires an active confirmed saved analysis")
        if (
            state.review.repository != "constructed/export"
            or state.review.review_id != report.review_id
            or state.review.head_sha != report.reviewed_head_sha
            or run.head != report.reviewed_head_sha
            or external.runs[-1].head_sha != report.reviewed_head_sha
            or state.review.final_acceptance
            or state.resolution_events
            or state.bundle.runtime_evidence
        ):
            raise ValueError("constructed inputs differ from the original review context")
        statuses = criterion_ci_statuses(state.bundle, external)
        outcomes = {
            test.test_id: CI_STATUS_LABELS[test.status]
            for row in statuses for test in row.tests
        }
        if outcomes != report.outcomes:
            raise ValueError("reported CI outcomes differ from the validated manifest")
        files.update({manifest_name: manifest_raw, run_name: run_raw, record_name: record_raw})
        files[report.report] = _label_report(raw)
        steps.append(WalkthroughStep(
            label=report.case, head_sha=report.reviewed_head_sha, report=report.report,
            original_report_sha256=report.report_sha256,
            review_sha256=report.review_record_sha256, manifest_sha256=report.manifest_sha256,
            outcomes=outcomes,
            result_runs={test.test_id: test.run_ids for row in statuses for test in row.tests},
            executed_tests=tuple(check.test for check in run.checks if check.outcome != "not_run"),
            gate=state.bundle.gate.verdict.value,
            review_status=review_status_label(state.bundle.gate.verdict),
            final_acceptance=state.review.final_acceptance,
        ))
    files["index.html"] = _index(tuple(steps), producer)
    manifest = WalkthroughManifest(
        schema_version="scopeproof-ci-walkthrough-v1",
        boundary="Constructed example; no target runtime, human acceptance or customer use.",
        original_producer=producer, original_provenance_sha256=sha256(original).hexdigest(),
        presentation_recipe=_artifact(
            "scripts/build_ci_walkthrough.py", Path(__file__).read_bytes(),
        ),
        steps=tuple(steps),
        artifacts=tuple(_artifact(name, raw) for name, raw in sorted(files.items())),
        human_use=False, target_runtime_verified=False,
    )
    files["provenance.json"] = (manifest.model_dump_json(indent=2) + "\n").encode()
    WalkthroughManifest.model_validate_json(files["provenance.json"])
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, payload in sorted(files.items()):
            entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, payload, compress_type=ZIP_DEFLATED, compresslevel=9)
    files[_ARCHIVE] = buffer.getvalue()
    receipt = DownloadReceipt(
        archive=_artifact(_ARCHIVE, files[_ARCHIVE]),
        provenance=_artifact("provenance.json", files["provenance.json"]),
    )
    files["download.json"] = (receipt.model_dump_json(indent=2) + "\n").encode()
    output.mkdir(parents=True, exist_ok=False)
    # Publish the entry point last, after all validated referenced artifacts.
    for name in [*sorted(set(files) - {"index.html"}), "index.html"]:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(files[name])
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="frozen original candidate artifacts")
    parser.add_argument("output", type=Path, help="new presentation directory")
    args = parser.parse_args()
    try:
        build_walkthrough(args.source, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Could not package walkthrough: {error}\n")
    print(args.output / "index.html")


if __name__ == "__main__":
    main()
