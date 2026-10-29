"""Produce one native v4 record with the installed, published ScopeProof 0.2.3.

Run with the verified old environment's Python, from outside this checkout:
    python -I /absolute/path/to/generate_record.py \
        --env-prefix /absolute/path/to/v023-env \
        --output-dir /absolute/path/to/old-native

This is constructed automation only: no target repository code, network requests,
actual target runtime, or human use. The old writer owns the saved JSON bytes.
The separate JSON stdout summary is validated with Pydantic before emission.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

REVIEW_ID = "constructed-v023-upgrade"
BOUNDARY = "Constructed automation only; no actual target runtime or human use."
CHECKOUT = Path(__file__).resolve().parents[3]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _guard_environment(env_prefix: Path, output_dir: Path) -> Path:
    """Reject repository imports or any interpreter except the specified old env."""
    _require(not Path.cwd().resolve().is_relative_to(CHECKOUT), "Run outside the checkout")
    _require(not env_prefix.is_relative_to(CHECKOUT), "Environment must be outside checkout")
    _require(not output_dir.is_relative_to(CHECKOUT), "Output must be outside checkout")
    _require(Path(sys.prefix).resolve() == env_prefix, "Interpreter prefix does not match")
    _require(importlib.metadata.version("scopeproof") == "0.2.3", "Requires scopeproof 0.2.3")
    distribution = importlib.metadata.distribution("scopeproof")
    _require(
        Path(distribution.locate_file("")).resolve().is_relative_to(env_prefix),
        "Distribution metadata must come from the specified environment",
    )
    spec = importlib.util.find_spec("scopeproof_core")
    _require(spec is not None and spec.origin is not None, "Installed core is missing")
    core_path = Path(spec.origin).resolve()
    _require(
        core_path.is_relative_to(env_prefix), "Core must import from the specified environment"
    )
    # Import only after its location is checked; never import checkout implementation.
    import scopeproof_core
    from scopeproof_core.storage.json_store import RECORD_VERSION

    _require(scopeproof_core.__version__ == "0.2.3", "Core version must be 0.2.3")
    _require(RECORD_VERSION == 4, "Old writer must use native record version 4")
    _require(
        not (output_dir / f"{REVIEW_ID}.json").exists()
        and not (output_dir / f"{REVIEW_ID}.json").is_symlink(),
        "Refusing to replace an existing record",
    )
    return core_path


def _generate(env_prefix: Path, output_dir: Path, core_path: Path) -> str:
    """Use supported old lifecycle/store APIs and return a validated summary."""
    from pydantic import BaseModel, ConfigDict, Field, create_model

    from scopeproof_core.criteria.confirmation import (
        CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
        build_criteria_source_provenance,
    )
    from scopeproof_core.demo import build_demo_review
    from scopeproof_core.reviews.lifecycle import (
        append_external_verification,
        append_resolution,
        attach_analysis,
        can_record_final_acceptance,
        confirm_criteria,
        new_review_state,
        revise_criteria,
    )
    from scopeproof_core.schemas.models import (
        EvidenceLevel,
        GateVerdict,
        HumanDecision,
        ResolutionEvent,
        ReviewState,
        RuntimeEvidence,
    )
    from scopeproof_core.storage.json_store import JsonReviewStore

    class GenerationSummary(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True)

        boundary: Literal[BOUNDARY]
        actual_target_runtime: Literal[False]
        human_use: Literal[False]
        package_version: Literal["0.2.3"]
        core_version: Literal["0.2.3"]
        record_version: Literal[4]
        environment_prefix: str
        core_import_path: str
        record_path: str
        record_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
        recipe_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
        packaged_fixture_path: str
        packaged_fixture_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
        packaged_labels_path: str
        packaged_labels_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
        review_id: Literal[REVIEW_ID]
        active_revision: Literal[2]
        historical_revisions: list[int]
        runtime_ids: list[str]
        event_ids: list[str]
        old_reader_active_gate: Literal["ready"]
        old_reader_historical_gates: list[Literal["ready"]]
        old_reader_exact_state_round_trip: Literal[True]
        old_reader_did_not_write: Literal[True]

    # Validate the whole native envelope without changing the writer's bytes.
    NativeRecord = create_model(
        "NativeV4Record",
        __config__=ConfigDict(extra="forbid"),
        record_version=(Literal[4], ...),
        saved_at=(datetime, ...),
        state=(ReviewState, ...),
    )

    def demo_bundle():
        bundle = build_demo_review()
        # Retain every packaged static caveat and add the explicit rehearsal boundary.
        for evidence in bundle.evidence:
            evidence.limitations = [f"{BOUNDARY} {item}" for item in evidence.limitations]
        return bundle

    def finish_revision(state, name: str, level: EvidenceLevel):
        _require(state.bundle is not None, "Revision must have attached analysis")
        runtime_id = f"constructed-{name}-runtime"
        evidence = RuntimeEvidence(
            runtime_evidence_id=runtime_id,
            repository=state.review.repository,
            pr_number=state.review.pr_number,
            head_sha=state.review.head_sha,
            criterion_id="AC-01",
            artifact_reference=f"scopeproof://constructed-automation/{name}",
            scenario=f"{BOUNDARY} Synthetic {name} CSV-export scenario.",
            environment=f"{BOUNDARY} Offline packaged-fixture rehearsal.",
            result=f"{BOUNDARY} Constructed passed value for persistence coverage.",
            reviewer=BOUNDARY,
            evidence_level=level,
            limitations=[f"{BOUNDARY} E3/E4 is a constructed schema value only."],
        )
        state = append_external_verification(
            state,
            evidence,
            ResolutionEvent(
                event_id=f"constructed-{name}-manual",
                criterion_id="AC-01",
                decision=HumanDecision.MANUALLY_VERIFIED,
                comment=f"{BOUNDARY} Constructed linked manual decision for persistence coverage.",
                claimed_evidence_level=level,
                runtime_evidence_id=runtime_id,
                reviewer=BOUNDARY,
            ),
        )
        for criterion in state.bundle.criteria:
            if criterion.criterion_id == "AC-01":
                continue
            state = append_resolution(
                state,
                ResolutionEvent(
                    event_id=f"constructed-{name}-accepted-{criterion.criterion_id}",
                    criterion_id=criterion.criterion_id,
                    decision=HumanDecision.ACCEPTED,
                    comment=f"{BOUNDARY} Constructed accepted value for persistence coverage.",
                    reviewer=BOUNDARY,
                ),
            )
        _require(can_record_final_acceptance(state), "Old final-acceptance prerequisites failed")
        state = append_resolution(
            state,
            ResolutionEvent(
                event_id=f"constructed-{name}-final-acceptance",
                final_acceptance=True,
                comment=f"{BOUNDARY} Constructed final-acceptance value for persistence coverage.",
                reviewer=BOUNDARY,
            ),
        )
        _require(state.bundle.gate.verdict is GateVerdict.READY, "Old gate did not calculate READY")
        return state

    def require_constructed_labels(state):
        bundles = [*state.analysis_history, state.bundle]
        labels = [event.reviewer for event in state.resolution_events]
        labels.extend(event.comment for event in state.resolution_events)
        labels.extend(
            provenance.confirmed_by
            for provenance in [
                state.review.criteria_source_provenance,
                state.criteria_revision.source_provenance,
                *(bundle.review.criteria_source_provenance for bundle in bundles),
            ]
        )
        for bundle in bundles:
            _require(bundle.review.input_origin.value == "constructed_demo", "Origin must be demo")
            for evidence in bundle.evidence:
                labels.extend(evidence.limitations)
            for evidence in bundle.runtime_evidence:
                labels.extend(
                    [evidence.reviewer, evidence.scenario, evidence.environment, evidence.result]
                )
                labels.extend(evidence.limitations)
            for resolution in bundle.resolutions:
                labels.extend([resolution.reviewer, resolution.comment])
        _require(
            bool(labels) and all(BOUNDARY in label for label in labels),
            "Every actor, confirmation, scenario, limitation and comment must state the boundary",
        )

    bundle = demo_bundle()
    bundle.review.review_id = REVIEW_ID
    bundle.review.criteria_source_provenance = build_criteria_source_provenance(
        source_uri=CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
        source_revision="constructed-automation-v023-upgrade-revision-1",
        source_text=bundle.source_text,
        criteria=bundle.criteria,
        confirmed_by=BOUNDARY,
        confirmed_at=datetime.now(UTC),
    )
    state = finish_revision(new_review_state(bundle), "historical", EvidenceLevel.E3)
    criteria = [item.model_copy(deep=True) for item in state.criteria_revision.criteria]
    criteria[0].text += " (constructed automation revision 2)"
    source_text = f"{state.criteria_revision.source_text}\n{BOUNDARY} Constructed revision 2."
    state = revise_criteria(state, criteria, source_text)
    provenance = build_criteria_source_provenance(
        source_uri=CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
        source_revision="constructed-automation-v023-upgrade-revision-2",
        source_text=source_text,
        criteria=criteria,
        confirmed_by=BOUNDARY,
        confirmed_at=datetime.now(UTC),
    )
    state = confirm_criteria(state, provenance)
    incoming = demo_bundle()
    incoming.review = state.review.model_copy(deep=True)
    incoming.criteria = [item.model_copy(deep=True) for item in criteria]
    incoming.source_text = source_text
    state = finish_revision(attach_analysis(state, incoming), "active", EvidenceLevel.E4)
    state = ReviewState.model_validate(state.model_dump(mode="python"))
    _require(len(state.analysis_history) == 1, "Expected exactly one historical analysis")
    _require(state.criteria_revision.number == 2, "Expected exactly two criteria revisions")
    _require(
        state.analysis_history[0].gate.verdict is GateVerdict.READY,
        "Historical old gate must be READY before saving",
    )
    require_constructed_labels(state)

    store = JsonReviewStore(output_dir)
    # One save only. Never downgrade, rewrite, or resave the native old record.
    path = store.save(state)
    original_bytes = path.read_bytes()
    native = NativeRecord.model_validate_json(original_bytes)
    _require(native.state == state, "Native envelope does not preserve generated state")
    loaded = store.load(REVIEW_ID)
    _require(loaded == state, "Old reader did not exactly round-trip generated state")
    _require(loaded.bundle.gate.verdict is GateVerdict.READY, "Old active gate changed")
    _require(
        all(item.gate.verdict is GateVerdict.READY for item in loaded.analysis_history),
        "Old historical gate changed",
    )
    _require(path.read_bytes() == original_bytes, "Old readback changed saved bytes")
    require_constructed_labels(loaded)

    package_root = core_path.parent.parent
    fixture = package_root / "evals" / "fixtures" / "csv_export_pr.json"
    labels = package_root / "evals" / "labels" / "csv_export_expected.json"
    summary = GenerationSummary(
        boundary=BOUNDARY,
        actual_target_runtime=False,
        human_use=False,
        package_version="0.2.3",
        core_version="0.2.3",
        record_version=4,
        environment_prefix=str(env_prefix),
        core_import_path=str(core_path),
        record_path=str(path),
        record_sha256=hashlib.sha256(original_bytes).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        packaged_fixture_path=str(fixture),
        packaged_fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
        packaged_labels_path=str(labels),
        packaged_labels_sha256=hashlib.sha256(labels.read_bytes()).hexdigest(),
        review_id=REVIEW_ID,
        active_revision=2,
        historical_revisions=[item.criteria_revision_number for item in loaded.analysis_history],
        runtime_ids=[
            item.runtime_evidence_id
            for bundle in [*loaded.analysis_history, loaded.bundle]
            for item in bundle.runtime_evidence
        ],
        event_ids=[item.event_id for item in loaded.resolution_events],
        old_reader_active_gate=loaded.bundle.gate.verdict.value,
        old_reader_historical_gates=[item.gate.verdict.value for item in loaded.analysis_history],
        old_reader_exact_state_round_trip=True,
        old_reader_did_not_write=True,
    )
    return summary.model_dump_json(indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-prefix", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    env_prefix = args.env_prefix.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    core_path = _guard_environment(env_prefix, output_dir)
    print(_generate(env_prefix, output_dir, core_path))


if __name__ == "__main__":
    main()
