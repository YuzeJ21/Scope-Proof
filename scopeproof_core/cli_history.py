"""Explicit historical-only CLI handoff over the existing saved-record services."""

from __future__ import annotations

import argparse
from pathlib import Path

from scopeproof_core.reporting.criteria_comparison import (
    export_criteria_comparison_json,
    export_criteria_comparison_markdown,
)
from scopeproof_core.reporting.historical_analysis import (
    export_historical_json,
    export_historical_markdown,
)
from scopeproof_core.reviews.criteria_comparison import (
    locked_criteria_comparison,
    prepare_criteria_comparison,
)
from scopeproof_core.reviews.historical_analysis import (
    locked_historical_analysis,
    prepare_historical_analysis,
)
from scopeproof_core.reviews.history_catalog import HistoricalExportRequest, build_history_catalog
from scopeproof_core.storage.atomic_files import atomic_create_text_with_receipt
from scopeproof_core.storage.json_store import JsonReviewStore


def _require_owner(review_id: str, saved_id: str) -> None:
    if review_id != saved_id:
        raise ValueError("saved filename and historical owner identity differ")


def _history(args: argparse.Namespace) -> int:
    store = JsonReviewStore(Path(args.storage_dir))
    with store.locked_load(args.review_id) as state:
        _require_owner(args.review_id, state.review.review_id)
        catalog = build_history_catalog(state)
        print(catalog.model_dump_json())
    return 0


def _export_history(args: argparse.Namespace) -> int:
    request = HistoricalExportRequest(
        review_id=args.review_id, history_position=args.history_position,
        expected_state_fingerprint=args.expected_state_fingerprint,
    )
    store = JsonReviewStore(Path(args.storage_dir))
    with store.locked_load(request.review_id) as state:
        _require_owner(request.review_id, state.review.review_id)
        if store.state_fingerprint(state) != request.expected_state_fingerprint:
            raise ValueError("saved history changed; run history and explicitly select again")
    # Store locks are non-reentrant. Both services recheck the detached snapshot after this lock.
    selection = prepare_historical_analysis(store, state, request.history_position - 1)
    with locked_historical_analysis(store, selection) as report:
        rendered = (export_historical_json(report) if args.format == "json"
                    else export_historical_markdown(report))
        if args.output is None:
            print(rendered, end="")
        else:
            atomic_create_text_with_receipt(Path(args.output), rendered)
    return 0


def _export_criteria_changes(args: argparse.Namespace) -> int:
    request = HistoricalExportRequest(
        review_id=args.review_id, history_position=args.history_position,
        expected_state_fingerprint=args.expected_state_fingerprint,
    )
    store = JsonReviewStore(Path(args.storage_dir))
    with store.locked_load(request.review_id) as state:
        _require_owner(request.review_id, state.review.review_id)
        if store.state_fingerprint(state) != request.expected_state_fingerprint:
            raise ValueError("saved requirements changed; run history and explicitly select again")
    # Preparation rechecks the detached saved state; never nest non-reentrant record locks.
    selection = prepare_criteria_comparison(store, state, request.history_position - 1)
    with locked_criteria_comparison(store, selection) as report:
        rendered = (export_criteria_comparison_json(report) if args.format == "json"
                    else export_criteria_comparison_markdown(report))
        if args.output is None:
            print(rendered, end="")
        else:
            atomic_create_text_with_receipt(Path(args.output), rendered)
    return 0


def register_history_commands(commands: argparse._SubParsersAction) -> None:
    history = commands.add_parser(
        "history", help="Describe retained historical analyses in one saved record",
    )
    history.add_argument("review_id")
    history.add_argument("--storage-dir", default=".scopeproof/reviews")
    history.set_defaults(handler=_history)
    export = commands.add_parser(
        "export-history", help="Export one explicit historical analysis; never current authority",
    )
    export.add_argument("review_id")
    export.add_argument("--history-position", type=int, required=True,
                        help="One-based retained position from history; no default")
    export.add_argument("--expected-state-fingerprint", required=True,
                        help="Exact saved-state fingerprint from history")
    export.add_argument("--format", choices=["json", "markdown"], default="json")
    export.add_argument("--output", help="Atomically create a new file without overwriting")
    export.add_argument("--storage-dir", default=".scopeproof/reviews")
    export.set_defaults(handler=_export_history)
    criteria = commands.add_parser(
        "export-criteria-changes",
        help="Export saved requirements changes; not evidence comparison",
    )
    criteria.add_argument("review_id")
    criteria.add_argument("--history-position", type=int, required=True,
                          help="One-based retained position from history; no default")
    criteria.add_argument("--expected-state-fingerprint", required=True,
                          help="Exact saved-state fingerprint from history")
    criteria.add_argument("--format", choices=["json", "markdown"], default="json")
    criteria.add_argument("--output", help="Atomically create a new file without overwriting")
    criteria.add_argument("--storage-dir", default=".scopeproof/reviews")
    criteria.set_defaults(handler=_export_criteria_changes)
