"""Explicit local saved-record transfer commands."""

import argparse
from pathlib import Path

from scopeproof_core.storage.json_store import JsonReviewStore
from scopeproof_core.storage.transfer import export_review, import_review


def _export_review(args: argparse.Namespace) -> int:
    receipt = export_review(
        JsonReviewStore(Path(args.storage_dir)), args.review_id, Path(args.output),
    )
    print(receipt.model_dump_json())
    return 0


def _import_review(args: argparse.Namespace) -> int:
    receipt = import_review(JsonReviewStore(Path(args.storage_dir)), Path(args.input))
    print(receipt.model_dump_json())
    return 0


def register_transfer_commands(commands: argparse._SubParsersAction) -> None:
    export = commands.add_parser(
        "export-review", help="Transfer a complete saved record, preserving history and provenance",
    )
    export.add_argument("review_id")
    export.add_argument("--storage-dir", default=".scopeproof/reviews")
    export.add_argument("--output", required=True, help="New local file; never overwrite")
    export.set_defaults(handler=_export_review)
    restore = commands.add_parser(
        "import-review", help="Validate and import a saved record under its original ID",
    )
    restore.add_argument("--input", required=True, help="Saved record from export-review")
    restore.add_argument("--storage-dir", default=".scopeproof/reviews")
    restore.set_defaults(handler=_import_review)
