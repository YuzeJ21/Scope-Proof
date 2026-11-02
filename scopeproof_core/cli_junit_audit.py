"""Typed, explicit CLI catalog and locked withdrawal of retained JUnit context."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scopeproof_core.reviews.junit_audit import (
    junit_import_status,
    junit_import_withdrawal_event,
    withdraw_junit_evidence_import,
)
from scopeproof_core.schemas.models import (
    MAX_JUNIT_IMPORTS_PER_REVIEW,
    GateVerdict,
    JUnitImportWithdrawalEvent,
    LocalReviewId,
)
from scopeproof_core.storage.json_store import JsonReviewStore


class JUnitImportCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    import_id: LocalReviewId
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mapped_criterion_ids: list[str] = Field(min_length=1)
    status: Literal["active", "withdrawn"]
    withdrawal_event: JUnitImportWithdrawalEvent | None


class JUnitImportCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: LocalReviewId
    state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    active_analysis_available: bool
    imports: list[JUnitImportCatalogEntry] = Field(max_length=MAX_JUNIT_IMPORTS_PER_REVIEW)
    evidence_boundary: Literal["externally_supplied_non_gating"] = "externally_supplied_non_gating"


class JUnitWithdrawalMutationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: LocalReviewId
    record: str
    state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    event: JUnitImportWithdrawalEvent
    verdict: GateVerdict
    final_acceptance: bool
    evidence_boundary: Literal["externally_supplied_non_gating"] = "externally_supplied_non_gating"


def _junit_imports(args: argparse.Namespace) -> int:
    store = JsonReviewStore(Path(args.storage_dir))
    with store.locked_load(args.review_id) as state:
        if state.review.review_id != args.review_id:
            raise ValueError("saved filename and JUnit audit owner differ")
        bundle = state.bundle
        catalog = JUnitImportCatalog(
            review_id=state.review.review_id,
            state_fingerprint=store.state_fingerprint(state),
            active_analysis_available=bundle is not None,
            imports=[
                JUnitImportCatalogEntry(
                    import_id=item.import_id,
                    artifact_sha256=item.artifact_sha256,
                    mapped_criterion_ids=[
                        mapping.criterion_id for mapping in item.criterion_mappings
                    ],
                    status=junit_import_status(bundle, item.import_id),
                    withdrawal_event=junit_import_withdrawal_event(bundle, item.import_id),
                )
                for item in bundle.junit_evidence_imports
            ]
            if bundle is not None
            else [],
        )
        print(catalog.model_dump_json())
    return 0


def _withdraw_junit(args: argparse.Namespace) -> int:
    store = JsonReviewStore(Path(args.storage_dir))

    def transition(state):
        if state.review.review_id != args.review_id:
            raise ValueError("saved filename and JUnit audit owner differ")
        return withdraw_junit_evidence_import(
            state,
            import_id=args.import_id,
            reviewer=args.reviewer,
            reason=args.reason,
            expected_state_fingerprint=args.expected_state_fingerprint,
        )

    state, path = store.mutate(args.review_id, transition)
    assert state.bundle is not None
    result = JUnitWithdrawalMutationMetadata(
        review_id=state.review.review_id,
        record=str(path),
        state_fingerprint=store.state_fingerprint(state),
        event=state.bundle.junit_import_events[-1],
        verdict=state.bundle.gate.verdict,
        final_acceptance=state.review.final_acceptance,
    )
    print(result.model_dump_json())
    return 0


def register_junit_audit_commands(commands: argparse._SubParsersAction) -> None:
    catalog = commands.add_parser(
        "junit-imports", help="Describe retained active-analysis JUnit imports"
    )
    catalog.add_argument("review_id")
    catalog.add_argument("--storage-dir", default=".scopeproof/reviews")
    catalog.set_defaults(handler=_junit_imports)
    withdraw = commands.add_parser(
        "withdraw-junit", help="Audit withdrawal of one whole saved import"
    )
    withdraw.add_argument("review_id")
    withdraw.add_argument("--storage-dir", default=".scopeproof/reviews")
    withdraw.add_argument("--import-id", required=True)
    withdraw.add_argument("--reviewer", required=True)
    withdraw.add_argument("--reason", required=True)
    withdraw.add_argument("--expected-state-fingerprint", required=True)
    withdraw.set_defaults(handler=_withdraw_junit)
