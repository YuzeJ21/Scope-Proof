"""Inline HTML code must not leave Markdown links active in new audit values."""

from scopeproof_core.reporting.exporters import export_comparison_markdown, export_markdown
from scopeproof_core.reviews.comparison import compare_reviews
from scopeproof_core.reviews.junit_audit import withdraw_junit_evidence_import
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.junit_audit_fixture import junit_audit_state


def test_new_withdrawal_metadata_escapes_markdown_links_in_both_handoffs():
    previous = junit_audit_state()
    current = withdraw_junit_evidence_import(
        previous, import_id="constructed-junit-import",
        reviewer="[Constructed actor](https://example.invalid/actor)",
        reason="[Constructed reason](https://example.invalid/reason)",
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(previous),
    )
    for text in (export_markdown(current),
                 export_comparison_markdown(compare_reviews(previous.bundle, current.bundle))):
        assert r"\[Constructed actor\]\(" in text
        assert r"\[Constructed reason\]\(" in text
        assert "[Constructed actor](https://" not in text
        assert "[Constructed reason](https://" not in text
