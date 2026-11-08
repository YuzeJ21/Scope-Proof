"""Build the no-install example with the actual installed public v0.2.6 package.

Run with that isolated environment's Python -I, outside the checkout. This recipe
reads the existing immutable constructed record and never saves or revises it.
"""

from __future__ import annotations

import argparse
import io
import sys
import zipfile
from hashlib import sha256
from importlib import metadata, util
from pathlib import Path
from typing import Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

RELEASE_SOURCE = "68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1"
PUBLIC_CORE = "7b3a9180fa8658e800486cac4cc0cb1a3ff236bb88c0ad9c9f165a699e04eb64"
PUBLIC_WHEEL = "48b308b3f92d912932734aa4907e958d78351bb956f1a9ce65353e9206741896"
INPUT_SHA256 = "044793a5894c13da7bd846f6926bbeac39955389c8897cdecaaf0bbe4e7b0ba5"
INPUT_PATH = "tests/fixtures/released_v026_upgrade/active-rich-v9.json"
RECIPE_PATH = "scripts/build_offline_handoff_sample.py"
REPORT_NAME = "constructed-v026-review.html"
ARCHIVE_NAME = "constructed-v026-review.zip"
SAMPLE_DISCLOSURE = (
    '<aside aria-label="Constructed sample disclosure" '
    'style="border:3px solid #b45309;padding:1rem;margin-bottom:1.5rem">'
    "<strong>CONSTRUCTED EXAMPLE — NOT A REAL REVIEW</strong>"
    "<p>This is an automated demonstration: no actual target runtime or human use. "
    "All recorded actors, decisions, CI metadata and runtime statements are simulated. "
    "Repository/head/source links are synthetic and do not resolve to a genuine reviewed PR.</p>"
    "<p>Expected current result: Action required; recorded final acceptance: No. "
    "This active review report includes recorded audit context. It is not an importable "
    "saved record or an export of every historical analysis.</p></aside>"
)


class StrictRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    @field_validator("*", mode="before")
    @classmethod
    def exact_literal_types(cls, value: object, info: ValidationInfo) -> object:
        annotation = cls.model_fields[info.field_name].annotation
        if get_origin(annotation) is Literal and not any(
            type(value) is type(option) and value == option for option in get_args(annotation)
        ):
            raise ValueError("literal values require their exact recorded type")
        return value


class Digest(StrictRecord):
    bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class Artifact(Digest):
    name: str = Field(min_length=1)


class SampleManifest(StrictRecord):
    schema_version: Literal["scopeproof-offline-handoff-sample-v1"]
    boundary: Literal["Constructed automation only; no actual target runtime or human use."]
    package_version: Literal["0.2.6"]
    release_source_commit: Literal[RELEASE_SOURCE]
    exporter_core_sha256: Literal[PUBLIC_CORE]
    public_wheel_sha256: Literal[PUBLIC_WHEEL]
    input_record: Artifact
    recipe: Artifact
    exported_html: Digest
    presented_report: Artifact
    download_archive: Artifact
    presentation_transform: Literal["one constructed-example disclosure immediately after body"]
    review_id: Literal["constructed-v026-active-rich"]
    criteria_revision_number: Literal[2]
    active_gate: Literal["blocked"]
    recorded_final_acceptance: Literal[False]
    actual_target_runtime: Literal[False]
    human_use: Literal[False]
    network_access_during_export: Literal[False]

    @model_validator(mode="after")
    def exact_artifact_roles(self):
        if (self.input_record.name, self.input_record.sha256) != (INPUT_PATH, INPUT_SHA256):
            raise ValueError("sample requires the unchanged native public-writer record")
        if (
            self.recipe.name != RECIPE_PATH
            or self.presented_report.name != REPORT_NAME
            or self.download_archive.name != ARCHIVE_NAME
        ):
            raise ValueError("sample artifact roles differ from this recipe")
        return self


def label_sample_report(rendered: str) -> str:
    """Add a disclosure, leaving every byte of the actual export body intact."""
    if rendered.count("<body>") != 1 or SAMPLE_DISCLOSURE in rendered:
        raise ValueError("requires one unlabelled exporter body")
    return rendered.replace("<body>", "<body>" + SAMPLE_DISCLOSURE, 1)


def _artifact(name: str, raw: bytes) -> Artifact:
    return Artifact(name=name, bytes=len(raw), sha256=sha256(raw).hexdigest())


def build_sample(*, record: Path, wheel: Path, output_dir: Path) -> SampleManifest:
    """Export only with the verified public package; refuse output replacement."""
    checkout = Path(__file__).resolve().parents[1]
    prefix = Path(sys.prefix).resolve()
    output = output_dir.resolve()
    if Path.cwd().resolve().is_relative_to(checkout) or prefix.is_relative_to(checkout):
        raise ValueError("run outside the checkout with an isolated installed public environment")
    if output.is_relative_to(checkout) or output.exists() or output_dir.is_symlink():
        raise ValueError("output must be a new directory outside the checkout")
    if metadata.version("scopeproof") != "0.2.6":
        raise ValueError("requires actual installed public ScopeProof 0.2.6")
    spec = util.find_spec("scopeproof_core")
    if (
        spec is None
        or spec.origin is None
        or not Path(spec.origin).resolve().is_relative_to(prefix)
    ):
        raise ValueError("core must import from the selected installed environment")
    if (
        not Path(metadata.distribution("scopeproof").locate_file(""))
        .resolve()
        .is_relative_to(prefix)
    ):
        raise ValueError("distribution metadata must belong to the installed environment")
    if sha256(wheel.read_bytes()).hexdigest() != PUBLIC_WHEEL:
        raise ValueError("wheel differs from the verified public download")
    original = record.read_bytes()
    if sha256(original).hexdigest() != INPUT_SHA256:
        raise ValueError("native record bytes changed")

    from scopeproof_core.build_identity import current_core_source_identity
    from scopeproof_core.reporting.exporters import export_html
    from scopeproof_core.storage.json_store import JsonReviewStore

    if current_core_source_identity().sha256 != PUBLIC_CORE:
        raise ValueError("installed core differs from the public release")

    def deny_external_execution(event, _args):
        if event in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"} or (
            event.startswith("os.exec")
        ):
            raise RuntimeError(f"offline sample export forbids {event}")

    sys.addaudithook(deny_external_execution)
    state = JsonReviewStore.decode_record(original.decode("utf-8"), require_recorded_facts=True)
    before = state.model_dump(mode="python")
    if state.bundle is None:
        raise ValueError("sample requires a confirmed active full review")
    bundle = state.bundle
    if (
        bundle.review.tool_version != "0.2.6"
        or bundle.review.input_origin.value != "constructed_demo"
    ):
        raise ValueError("sample must retain its actual constructed release producer")
    if bundle.review.analysis_source_identity.sha256 != PUBLIC_CORE:
        raise ValueError("recorded analysis producer differs from the public writer")
    raw_html = export_html(state)
    if raw_html != export_html(state) or state.model_dump(mode="python") != before:
        raise ValueError("export must be reproducible and leave recorded state intact")
    presented = label_sample_report(raw_html).encode("utf-8")
    archive_buffer = io.BytesIO()
    entry = zipfile.ZipInfo(REPORT_NAME, date_time=(1980, 1, 1, 0, 0, 0))
    entry.create_system = 3
    entry.external_attr = 0o100644 << 16
    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(entry, presented, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    archive_bytes = archive_buffer.getvalue()
    if record.read_bytes() != original:
        raise ValueError("input record changed during export")
    manifest = SampleManifest(
        schema_version="scopeproof-offline-handoff-sample-v1",
        boundary="Constructed automation only; no actual target runtime or human use.",
        package_version=metadata.version("scopeproof"),
        release_source_commit=RELEASE_SOURCE,
        exporter_core_sha256=current_core_source_identity().sha256,
        public_wheel_sha256=PUBLIC_WHEEL,
        input_record=_artifact(INPUT_PATH, original),
        recipe=_artifact(RECIPE_PATH, Path(__file__).read_bytes()),
        exported_html=Digest(
            bytes=len(raw_html.encode("utf-8")), sha256=sha256(raw_html.encode("utf-8")).hexdigest()
        ),
        presented_report=_artifact(REPORT_NAME, presented),
        download_archive=_artifact(ARCHIVE_NAME, archive_bytes),
        presentation_transform="one constructed-example disclosure immediately after body",
        review_id=bundle.review.review_id,
        criteria_revision_number=state.criteria_revision.number,
        active_gate=bundle.gate.verdict.value,
        recorded_final_acceptance=bundle.review.final_acceptance,
        actual_target_runtime=False,
        human_use=False,
        network_access_during_export=False,
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / REPORT_NAME).write_bytes(presented)
    (output / ARCHIVE_NAME).write_bytes(archive_bytes)
    (output / "provenance.json").write_text(
        manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    SampleManifest.model_validate_json((output / "provenance.json").read_bytes())
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    print(
        build_sample(
            record=args.record, wheel=args.wheel, output_dir=args.output_dir
        ).model_dump_json(indent=2)
    )
