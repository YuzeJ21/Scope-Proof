"""Frozen constructed CI inputs; no new source analysis or target execution."""

from pathlib import Path

from scopeproof_core.reviews.ci_status import load_ci_status_manifest
from scopeproof_core.storage.json_store import JsonReviewStore


def ci_comparison_inputs():
    root = Path(__file__).resolve().parents[1] / "docs/examples/ci-handoff/source/inputs"
    state = JsonReviewStore.decode_record(
        (root / "B-review.json").read_text(encoding="utf-8"), require_recorded_facts=True,
    )
    previous = (root / "B-scopeproof-manifest.json").read_bytes()
    current = (root / "B-targeted-scopeproof-manifest.json").read_bytes()
    return (
        state, load_ci_status_manifest(previous), load_ci_status_manifest(current),
        previous, current,
    )
