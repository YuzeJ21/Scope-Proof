"""Strict provenance for constructed records emitted by the public v0.2.6 writer."""

from datetime import datetime
from pathlib import PurePosixPath
from typing import Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

BOUNDARY = "Constructed automation only; no actual target runtime or human use."
TIMESTAMPS_NOTE = (
    "Record timestamps belong to constructed automation, not human actions or target-runtime "
    "observations; generated_at_utc records corpus generation."
)
RELEASE_SOURCE_COMMIT = "68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1"
CORE_SHA256 = "7b3a9180fa8658e800486cac4cc0cb1a3ff236bb88c0ad9c9f165a699e04eb64"
PUBLIC_WHEEL_SHA256 = "48b308b3f92d912932734aa4907e958d78351bb956f1a9ce65353e9206741896"
PUBLIC_CHECKSUMS_SHA256 = "b6f6f3833ce0479812eb42994dfc5aec2ea23907ec3f9ed55a3085ae01cd3252"
REVIEW_IDS = {case: f"constructed-v026-{case}" for case in ("active-rich", "pending-rich")}
FIXTURE_NAMES = {case: f"{case}-v9.json" for case in REVIEW_IDS}


class StrictProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    @field_validator("*", mode="before")
    @classmethod
    def exact_literal_types(cls, value: object, info: ValidationInfo) -> object:
        # Literal equality otherwise accepts 0 as False and 9.0 as integer 9.
        annotation = cls.model_fields[info.field_name].annotation
        if annotation is datetime and info.mode == "json" and isinstance(value, str):
            # A before-validator receives JSON strings before strict datetime parsing.
            return datetime.fromisoformat(value)
        if get_origin(annotation) is Literal and not any(
            type(value) is type(option) and value == option for option in get_args(annotation)
        ):
            raise ValueError("literal values require their exact recorded type")
        return value


class ArtifactDigest(StrictProvenance):
    name: str = Field(min_length=1)
    bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("name")
    @classmethod
    def relative_artifact_name(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value:
            raise ValueError("artifact names must be relative and portable")
        return value


class CoverageCounts(StrictProvenance):
    historical_analyses: Literal[1, 2]
    resolution_events: Literal[9]
    runtime_records: Literal[2]
    selected_references: Literal[4]
    selected_reference_events: Literal[4]
    junit_imports: Literal[2]
    junit_events: Literal[4]
    scope_decisions: Literal[2]


class RecordProvenance(StrictProvenance):
    case: Literal["active-rich", "pending-rich"]
    record: ArtifactDigest
    review_id: str
    record_version: Literal[9]
    producer_tool_version: Literal["0.2.6"]
    producer_ruleset_version: Literal["2.0.0"]
    producer_core_sha256: Literal[CORE_SHA256]
    criteria_revision_number: Literal[2, 3]
    criteria_confirmed: bool
    has_active_analysis: bool
    historical_revision_numbers: list[int]
    active_gate: Literal["blocked"] | None
    historical_gates: list[Literal["ready", "blocked"]]
    runtime_evidence_ids: list[str] = Field(min_length=2, max_length=2)
    resolution_event_ids: list[str] = Field(min_length=9, max_length=9)
    counts: CoverageCounts

    @model_validator(mode="after")
    def expected_case(self) -> "RecordProvenance":
        pending = self.case == "pending-rich"
        expected = (
            (3, False, False, [1, 2], None, ["ready", "blocked"], 2)
            if pending
            else (2, True, True, [1], "blocked", ["ready"], 1)
        )
        actual = (
            self.criteria_revision_number,
            self.criteria_confirmed,
            self.has_active_analysis,
            self.historical_revision_numbers,
            self.active_gate,
            self.historical_gates,
            self.counts.historical_analyses,
        )
        if actual != expected:
            raise ValueError("record lifecycle does not match the named constructed case")
        if self.review_id != REVIEW_IDS[self.case] or self.record.name != FIXTURE_NAMES[self.case]:
            raise ValueError("record identity does not match the named constructed case")
        if len(set(self.runtime_evidence_ids)) != 2 or len(set(self.resolution_event_ids)) != 9:
            raise ValueError("constructed runtime and resolution IDs must be unique")
        return self


class ReleasedWriterProvenance(StrictProvenance):
    schema_version: Literal["scopeproof-released-v026-corpus-v1"]
    boundary: Literal[BOUNDARY]
    timestamps_note: Literal[TIMESTAMPS_NOTE]
    actual_target_runtime: Literal[False]
    human_use: Literal[False]
    network_access: Literal[False]
    generated_at_utc: datetime
    package_version: Literal["0.2.6"]
    core_version: Literal["0.2.6"]
    python_version: str
    release_source_commit: Literal[RELEASE_SOURCE_COMMIT]
    release_url: Literal["https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6"]
    installed_core_source_sha256: Literal[CORE_SHA256]
    installed_import_relative_to_environment: str
    public_wheel: ArtifactDigest
    public_checksums: ArtifactDigest
    recipe: ArtifactDigest
    provenance_schema: ArtifactDigest
    packaged_fixture: ArtifactDigest
    packaged_labels: ArtifactDigest
    records: list[RecordProvenance] = Field(min_length=2, max_length=2)
    native_round_trip_exact: Literal[True]
    load_preserved_original_bytes: Literal[True]
    limitations: list[str] = Field(min_length=4)

    @model_validator(mode="after")
    def release_binding(self) -> "ReleasedWriterProvenance":
        if self.public_wheel.name != "scopeproof-0.2.6-py3-none-any.whl":
            raise ValueError("public wheel name differs from the release")
        if self.public_wheel.sha256 != PUBLIC_WHEEL_SHA256:
            raise ValueError("public wheel digest differs from the release")
        if (
            self.public_checksums.name != "SHA256SUMS.txt"
            or self.public_checksums.sha256 != PUBLIC_CHECKSUMS_SHA256
        ):
            raise ValueError("public checksums differ from the release")
        ArtifactDigest.relative_artifact_name(self.installed_import_relative_to_environment)
        if [record.case for record in self.records] != ["active-rich", "pending-rich"]:
            raise ValueError("corpus requires the active and pending cases in order")
        if (
            self.generated_at_utc.utcoffset() is None
            or self.generated_at_utc.utcoffset().total_seconds()
        ):
            raise ValueError("generation timestamp must be UTC")
        return self
