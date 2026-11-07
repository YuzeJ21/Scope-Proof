"""Generate immutable constructed native-v9 records through public ScopeProof 0.2.6.

Run outside the checkout with the verified installed public wheel's Python:
    python -I /absolute/path/generate_records.py --env-prefix /absolute/public-env \
        --wheel /absolute/scopeproof-0.2.6-py3-none-any.whl \
        --checksums /absolute/SHA256SUMS.txt --output-dir /absolute/new-corpus

The sibling provenance_schema.py is part of this standalone trusted recipe.
Existing output directories are refused. CI reads committed bytes and never runs
this generator. All claims/actors are constructed; no target code is executed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

CHECKOUT = Path(__file__).resolve().parents[3]
BOUNDARY = "Constructed automation only; no actual target runtime or human use."
ACTOR = f"CONSTRUCTED compatibility actor. {BOUNDARY}"
SOURCE_BASE, SOURCE_HEAD = "b" * 40, "a" * 40


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def schema_module():
    path = Path(__file__).with_name("provenance_schema.py")
    spec = importlib.util.spec_from_file_location("released_v026_provenance", path)
    require(spec is not None and spec.loader is not None, "Provenance schema is missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def artifact(schema, path: Path, name: str | None = None):
    raw = path.read_bytes()
    return schema.ArtifactDigest(
        name=name or path.name,
        bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def guard(args, schema) -> Path:
    prefix, output = args.env_prefix.resolve(), args.output_dir.resolve()
    require(
        sys.flags.isolated == 1 and sys.prefix != sys.base_prefix,
        "Use Python -I in the installed public environment",
    )
    require(Path(sys.prefix).resolve() == prefix, "Interpreter prefix differs")
    require(not Path.cwd().resolve().is_relative_to(CHECKOUT), "Run outside checkout")
    require(not prefix.is_relative_to(CHECKOUT), "Environment must be outside checkout")
    require(not output.is_relative_to(CHECKOUT), "Output must be outside checkout")
    require(
        not output.exists() and not args.output_dir.is_symlink(),
        "Refusing to replace an existing output directory",
    )
    require(importlib.metadata.version("scopeproof") == "0.2.6", "Requires public 0.2.6")
    distribution = importlib.metadata.distribution("scopeproof")
    require(
        Path(distribution.locate_file("")).resolve().is_relative_to(prefix),
        "Distribution metadata must be installed in the selected environment",
    )
    spec = importlib.util.find_spec("scopeproof_core")
    require(spec is not None and spec.origin is not None, "Installed core is missing")
    core = Path(spec.origin).resolve()
    require(core.is_relative_to(prefix), "Core must import from the selected environment")
    import scopeproof_core
    from scopeproof_core.build_identity import current_core_source_identity
    from scopeproof_core.storage.json_store import RECORD_VERSION

    require(
        scopeproof_core.__version__ == "0.2.6" and RECORD_VERSION == 9,
        "Requires actual released core 0.2.6 and native record version 9",
    )
    require(
        current_core_source_identity().sha256 == schema.CORE_SHA256,
        "Installed core differs from the public release",
    )
    require(
        artifact(schema, args.wheel).sha256 == schema.PUBLIC_WHEEL_SHA256,
        "Wheel differs from the verified public download",
    )
    require(
        artifact(schema, args.checksums).sha256 == schema.PUBLIC_CHECKSUMS_SHA256,
        "Checksums differ from the verified public download",
    )
    require(
        f"{schema.PUBLIC_WHEEL_SHA256}  {args.wheel.name}"
        in args.checksums.read_text(encoding="utf-8").splitlines(),
        "Public checksum manifest does not bind this wheel",
    )

    def deny_external_execution(event, _args):
        if event in {
            "socket.connect",
            "socket.getaddrinfo",
            "subprocess.Popen",
            "os.system",
        } or event.startswith("os.exec"):
            raise RuntimeError(f"Offline recipe forbids {event}")

    sys.addaudithook(deny_external_execution)
    return core


def bundles(state):
    return [*state.analysis_history, *([state.bundle] if state.bundle is not None else [])]


def assert_constructed(state) -> None:
    """Reject unlabelled attribution and accidental producer replacement."""
    for bundle in bundles(state):
        require(bundle.review.tool_version == "0.2.6", "Requires the actual installed writer")
        require(bundle.review.input_origin.value == "constructed_demo", "Origin must stay demo")

    def inspect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"reviewer", "imported_by", "confirmed_by"}:
                    require(item == ACTOR, "Every actor must be explicitly constructed")
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)

    inspect(state.model_dump(mode="json"))


def make_native_state(review_id: str, pending: bool):
    """Exercise published product APIs; do not assign a historical producer version."""
    from scopeproof_core.criteria.confirmation import (
        CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
        build_criteria_source_provenance,
    )
    from scopeproof_core.demo import build_review, load_demo_labels, load_demo_snapshot
    from scopeproof_core.gates.evaluator import evaluate_gate
    from scopeproof_core.gates.validation import validated_review_state
    from scopeproof_core.importers.junit import JUnitMappingSelection, build_junit_evidence_import
    from scopeproof_core.reviews.junit_audit import withdraw_junit_evidence_import
    from scopeproof_core.reviews.junit_correction import correct_junit_mappings
    from scopeproof_core.reviews.lifecycle import (
        append_external_verification,
        append_file_scope_decision,
        append_junit_evidence_import,
        append_resolution,
        attach_analysis,
        can_record_final_acceptance,
        confirm_criteria,
        new_review_state,
        revise_criteria,
    )
    from scopeproof_core.reviews.reference_audit import (
        correct_reviewer_selected_reference,
        withdraw_reviewer_selected_reference,
    )
    from scopeproof_core.reviews.selected_references import (
        append_reviewer_selected_reference,
        selectable_reference_lines,
    )
    from scopeproof_core.schemas.models import (
        ChangedFile,
        ChangedLine,
        EvidenceLevel,
        FileScopeDecision,
        HumanDecision,
        JUnitCriterionMapping,
        LineChangeType,
        ResolutionEvent,
        RuntimeEvidence,
    )
    from scopeproof_core.storage.json_store import JsonReviewStore

    snapshot = load_demo_snapshot().model_copy(deep=True)
    # Explicitly synthetic exact-length coordinates permit JUnit provenance validation.
    snapshot.base_sha, snapshot.head_sha = SOURCE_BASE, SOURCE_HEAD
    snapshot.ci_observation.reason = f"{BOUNDARY} Synthetic passing metadata; no real CI run."
    snapshot.files.append(
        ChangedFile(
            path="notes/constructed-unrelated.txt",
            status="added",
            additions=1,
            changes=1,
            lines=[
                ChangedLine(
                    change_type=LineChangeType.ADDED,
                    line_number=1,
                    content="CONSTRUCTED unrelated housekeeping context",
                )
            ],
        )
    )

    def provenance(criteria, source_text, revision):
        return build_criteria_source_provenance(
            source_uri=CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
            source_revision=f"constructed-v026-compatibility-revision-{revision}",
            source_text=source_text,
            criteria=criteria,
            confirmed_by=ACTOR,
            confirmed_at=datetime.now(UTC),
        )

    initial = build_review(snapshot, load_demo_labels())
    initial.review.review_id = review_id
    initial.review.criteria_source_provenance = provenance(initial.criteria, initial.source_text, 1)
    initial.gate = evaluate_gate(
        initial.review, initial.criteria, initial.findings, [], initial.evidence
    )
    state = new_review_state(initial)

    def enrich(current, name, accepted):
        before_gate = current.bundle.gate.model_dump(mode="json")
        offered = selectable_reference_lines(current, snapshot)
        require(len(offered) >= 2, "Fixture must offer two distinct exact-head static lines")
        current = append_reviewer_selected_reference(
            current,
            snapshot=snapshot,
            selected=offered[0],
            criterion_id="AC-01",
            reviewer=ACTOR,
            rationale=f"{BOUNDARY} Constructed static selection.",
            expected_state_fingerprint=JsonReviewStore.state_fingerprint(current),
        )
        first = current.bundle.reviewer_selected_references[-1].reference_id
        current = correct_reviewer_selected_reference(
            current,
            reference_id=first,
            snapshot=snapshot,
            selected=offered[1],
            reviewer=ACTOR,
            rationale=f"{BOUNDARY} Constructed replacement context.",
            reason=f"{BOUNDARY} Rehearse attributable static-reference correction.",
            expected_state_fingerprint=JsonReviewStore.state_fingerprint(current),
        )
        replacement = current.bundle.reviewer_selected_references[-1].reference_id
        current = withdraw_reviewer_selected_reference(
            current,
            reference_id=replacement,
            reviewer=ACTOR,
            reason=f"{BOUNDARY} Rehearse terminal static-reference withdrawal.",
            expected_state_fingerprint=JsonReviewStore.state_fingerprint(current),
        )
        xml = (
            f'<testsuite name="CONSTRUCTED {name}">'
            '<testcase name="CONSTRUCTED pass"/>'
            '<testcase name="CONSTRUCTED failure"><failure/></testcase>'
            "</testsuite>"
        ).encode()
        import_id = f"constructed-{name}-junit"
        imported = build_junit_evidence_import(
            current,
            xml,
            [
                JUnitMappingSelection(scope_id="suite-0001-case-0001", criterion_id="AC-01"),
                JUnitMappingSelection(scope_id="suite-0001-case-0002", criterion_id="AC-02"),
            ],
            importer=ACTOR,
            limitations=[BOUNDARY],
            import_id=import_id,
        )
        current = append_junit_evidence_import(current, imported)
        current = correct_junit_mappings(
            current,
            import_id=import_id,
            criterion_mappings=[
                JUnitCriterionMapping(criterion_id="AC-01", test_case_ids=["suite-0001-case-0002"]),
                JUnitCriterionMapping(criterion_id="AC-02", test_case_ids=["suite-0001-case-0001"]),
            ],
            reviewer=ACTOR,
            reason=f"{BOUNDARY} Rehearse explicit mapping correction.",
            expected_state_fingerprint=JsonReviewStore.state_fingerprint(current),
            confirm_whole_import=True,
        )
        current = withdraw_junit_evidence_import(
            current,
            import_id=import_id,
            reviewer=ACTOR,
            reason=f"{BOUNDARY} Rehearse whole-import withdrawal.",
            expected_state_fingerprint=JsonReviewStore.state_fingerprint(current),
        )
        require(
            current.bundle.gate.model_dump(mode="json") == before_gate,
            "Non-gating references and imported assertions changed the gate",
        )
        current = append_file_scope_decision(
            current,
            FileScopeDecision(
                event_id=f"constructed-{name}-scope",
                review_id=current.review.review_id,
                path="notes/constructed-unrelated.txt",
                head_sha=current.review.head_sha,
                criteria_revision_number=current.criteria_revision.number,
                normalized_criteria_sha256=current.review.criteria_source_provenance.normalized_criteria_sha256,
                disposition="outside_confirmed_criteria",
                reviewer=ACTOR,
                note=f"{BOUNDARY} Housekeeping explicitly outside this constructed intent.",
            ),
        )
        runtime_id = f"constructed-{name}-runtime"
        level = EvidenceLevel.E3 if accepted else EvidenceLevel.E4
        current = append_external_verification(
            current,
            RuntimeEvidence(
                runtime_evidence_id=runtime_id,
                repository=current.review.repository,
                pr_number=current.review.pr_number,
                head_sha=current.review.head_sha,
                criterion_id="AC-01",
                artifact_reference=f"scopeproof://constructed/{name}",
                scenario=f"{BOUNDARY} Synthetic CSV persistence scenario.",
                environment=f"{BOUNDARY} Offline packaged-fixture rehearsal.",
                result=f"{BOUNDARY} Constructed passed schema value, not an observed test result.",
                reviewer=ACTOR,
                evidence_level=level,
                limitations=[BOUNDARY],
            ),
            ResolutionEvent(
                event_id=f"constructed-{name}-manual",
                criterion_id="AC-01",
                decision=HumanDecision.MANUALLY_VERIFIED,
                runtime_evidence_id=runtime_id,
                claimed_evidence_level=level,
                reviewer=ACTOR,
                comment=f"{BOUNDARY} Constructed linked decision, not actual verification.",
            ),
        )
        for criterion in current.bundle.criteria:
            if criterion.criterion_id == "AC-01":
                continue
            decision = HumanDecision.ACCEPTED
            if not accepted and criterion.criterion_id == "AC-03":
                decision = HumanDecision.CHANGE_REQUIRED
            current = append_resolution(
                current,
                ResolutionEvent(
                    event_id=f"constructed-{name}-{criterion.criterion_id}",
                    criterion_id=criterion.criterion_id,
                    decision=decision,
                    reviewer=ACTOR,
                    comment=f"{BOUNDARY} Explicit synthetic decision for compatibility coverage.",
                ),
            )
        if accepted:
            require(
                can_record_final_acceptance(current), "Constructed historical prerequisites failed"
            )
            current = append_resolution(
                current,
                ResolutionEvent(
                    event_id=f"constructed-{name}-acceptance",
                    final_acceptance=True,
                    reviewer=ACTOR,
                    comment=f"{BOUNDARY} Constructed final-acceptance flag, not genuine approval.",
                ),
            )
            require(current.bundle.gate.verdict.value == "ready", "Historical gate must be Ready")
        else:
            require(current.bundle.gate.verdict.value == "blocked", "Active gate must stay Blocked")
            require(current.review.final_acceptance is False, "Active acceptance must remain false")
        return current

    state = enrich(state, "historical", True)
    criteria = [item.model_copy(deep=True) for item in state.criteria_revision.criteria]
    criteria[0].text += " (CONSTRUCTED later revision)"
    source_text = f"{state.criteria_revision.source_text}\n{BOUNDARY} Revision two."
    state = revise_criteria(state, criteria, source_text)
    state = confirm_criteria(state, provenance(criteria, source_text, 2))
    incoming = build_review(snapshot, load_demo_labels())
    incoming.review = state.review.model_copy(deep=True)
    incoming.criteria = criteria
    incoming.source_text = source_text
    incoming.gate = evaluate_gate(
        incoming.review, criteria, incoming.findings, [], incoming.evidence
    )
    state = enrich(attach_analysis(state, incoming), "active", False)
    if pending:
        pending_criteria = [item.model_copy(deep=True) for item in state.criteria_revision.criteria]
        pending_criteria[-1].text += " (CONSTRUCTED pending clarification)"
        state = revise_criteria(
            state, pending_criteria, source_text + "\nCONSTRUCTED pending revision."
        )
        require(
            not state.criteria_revision.confirmed and state.bundle is None,
            "Pending record must remain unconfirmed without an active analysis",
        )
    state = validated_review_state(state)
    assert_constructed(state)
    return state


def generate(args, schema, core: Path):
    import scopeproof_core
    from scopeproof_core.build_identity import current_core_source_identity
    from scopeproof_core.schemas.models import ReviewState
    from scopeproof_core.storage.json_store import JsonReviewStore

    args.output_dir.mkdir(parents=True, exist_ok=False)
    records = []
    for case, review_id in schema.REVIEW_IDS.items():
        state = make_native_state(review_id, pending=case == "pending-rich")
        store = JsonReviewStore(args.output_dir / case)
        path = store.save(state)
        original = path.read_bytes()
        envelope = json.loads(original)
        require(envelope["record_version"] == 9, "Writer must emit native v9")
        require(
            ReviewState.model_validate(envelope["state"]) == state,
            "Native schema round-trip changed constructed state",
        )
        require(
            store.load(review_id).model_dump(mode="json") == envelope["state"],
            "Native writer readback changed a recorded fact",
        )
        require(path.read_bytes() == original, "Native writer load changed original bytes")
        retained = bundles(state)
        require(
            all(
                bundle.review.analysis_source_identity.sha256 == schema.CORE_SHA256
                for bundle in retained
            ),
            "Native producer identity differs",
        )
        destination = args.output_dir / schema.FIXTURE_NAMES[case]
        # Rename the native writer's file; never serialize or edit its bytes.
        path.rename(destination)
        require(destination.read_bytes() == original, "Moving native bytes changed the record")
        records.append(
            schema.RecordProvenance(
                case=case,
                record=artifact(schema, destination),
                review_id=review_id,
                record_version=envelope["record_version"],
                producer_tool_version=state.review.tool_version,
                producer_ruleset_version=state.review.ruleset_version,
                producer_core_sha256=state.review.analysis_source_identity.sha256,
                criteria_revision_number=state.criteria_revision.number,
                criteria_confirmed=state.criteria_revision.confirmed,
                has_active_analysis=state.bundle is not None,
                historical_revision_numbers=[
                    bundle.criteria_revision_number for bundle in state.analysis_history
                ],
                active_gate=state.bundle.gate.verdict.value if state.bundle else None,
                historical_gates=[bundle.gate.verdict.value for bundle in state.analysis_history],
                runtime_evidence_ids=[
                    item.runtime_evidence_id
                    for bundle in retained
                    for item in bundle.runtime_evidence
                ],
                resolution_event_ids=[event.event_id for event in state.resolution_events],
                counts=schema.CoverageCounts(
                    historical_analyses=len(state.analysis_history),
                    resolution_events=len(state.resolution_events),
                    runtime_records=sum(len(bundle.runtime_evidence) for bundle in retained),
                    selected_references=sum(
                        len(bundle.reviewer_selected_references) for bundle in retained
                    ),
                    selected_reference_events=sum(
                        len(bundle.selected_reference_events) for bundle in retained
                    ),
                    junit_imports=sum(len(bundle.junit_evidence_imports) for bundle in retained),
                    junit_events=sum(len(bundle.junit_import_events) for bundle in retained),
                    scope_decisions=sum(len(bundle.file_scope_decisions) for bundle in retained),
                ),
            )
        )
    result = schema.ReleasedWriterProvenance(
        schema_version="scopeproof-released-v026-corpus-v1",
        boundary=BOUNDARY,
        timestamps_note=schema.TIMESTAMPS_NOTE,
        actual_target_runtime=False,
        human_use=False,
        network_access=False,
        generated_at_utc=datetime.now(UTC),
        package_version=importlib.metadata.version("scopeproof"),
        core_version=scopeproof_core.__version__,
        python_version=sys.version.split()[0],
        release_source_commit=schema.RELEASE_SOURCE_COMMIT,
        release_url="https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6",
        installed_core_source_sha256=current_core_source_identity().sha256,
        installed_import_relative_to_environment=core.relative_to(
            args.env_prefix.resolve()
        ).as_posix(),
        public_wheel=artifact(schema, args.wheel),
        public_checksums=artifact(schema, args.checksums),
        recipe=artifact(schema, Path(__file__).resolve()),
        provenance_schema=artifact(schema, Path(__file__).with_name("provenance_schema.py")),
        packaged_fixture=artifact(
            schema,
            core.parent.parent / "evals/fixtures/csv_export_pr.json",
            "evals/fixtures/csv_export_pr.json",
        ),
        packaged_labels=artifact(
            schema,
            core.parent.parent / "evals/labels/csv_export_expected.json",
            "evals/labels/csv_export_expected.json",
        ),
        records=records,
        native_round_trip_exact=True,
        load_preserved_original_bytes=True,
        limitations=[
            "Two constructed native v9 histories, not all records, dependencies or platforms.",
            "Constructed actors, approvals, runtime values and check metadata supply no "
            "human or target-runtime credit.",
            "Recorded producer identity is distinct from a later reader's validation identity.",
            "No actor authentication, historical executable replay, live GitHub checks "
            "or downgrade guarantee.",
            "No genuine independent use, qualifying reviews, adoption "
            "or production-readiness evidence.",
            "Frozen benchmarks, prior fixtures and public release assets are unchanged.",
        ],
    )
    rendered = result.model_dump_json(indent=2) + "\n"
    schema.ReleasedWriterProvenance.model_validate_json(rendered)
    with (args.output_dir / "provenance.json").open("x", encoding="utf-8", newline="") as handle:
        handle.write(rendered)
    print(rendered, end="")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("env-prefix", "wheel", "checksums", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    schema = schema_module()
    generate(args, schema, guard(args, schema))


if __name__ == "__main__":
    main()
