"""CONSTRUCTED loaded diff, never practitioner or target-runtime evidence."""

from scopeproof_core.demo import build_review, load_demo_labels, load_demo_snapshot
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.schemas.models import ChangedFile, ChangedLine, LineChangeType


def scope_preview_context(*, status="modified", previous_path=None, lines=None):
    snapshot = load_demo_snapshot()
    snapshot.files.append(ChangedFile(
        path="notes.md", status=status, previous_path=previous_path,
        lines=lines if lines is not None else [
            ChangedLine(change_type=LineChangeType.REMOVED, line_number=20,
                        content="CONSTRUCTED old note"),
            ChangedLine(change_type=LineChangeType.ADDED, line_number=21,
                        content="CONSTRUCTED new note <img src=x> **Ready**"),
            ChangedLine(change_type=LineChangeType.CONTEXT, line_number=50,
                        content="CONSTRUCTED retained context"),
        ],
    ))
    return new_review_state(build_review(snapshot, load_demo_labels())), snapshot
