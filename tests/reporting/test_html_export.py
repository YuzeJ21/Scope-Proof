from scopeproof_core.demo import build_demo_review
from scopeproof_core.reporting.exporters import export_html
from scopeproof_core.schemas.models import GateVerdict
from tests.final_acceptance_fixture import acceptance_comparison_states


def test_html_export_is_self_contained_and_preserves_audit_identity() -> None:
    html = export_html(build_demo_review())
    assert "<!doctype html>" in html.lower()
    assert "scopeproof acceptance review" in html.lower()
    assert "head-demo-002" in html
    assert "does not replace QA" in html
    assert "<script" not in html.lower()


def test_html_export_escapes_evidence_excerpt() -> None:
    bundle = build_demo_review()
    bundle.evidence[0].excerpt = "<script>alert('unsafe')</script>"
    html = export_html(bundle)
    assert "&lt;script&gt;" in html
    assert "<script>alert" not in html


def test_html_export_escapes_review_provenance() -> None:
    bundle = build_demo_review()
    bundle.review.tool_version = "dev<unsafe>"
    bundle.review.ruleset_version = "rules<unsafe>"

    html = export_html(bundle)
    assert "dev&lt;unsafe&gt;" in html
    assert "rules&lt;unsafe&gt;" in html
    assert "dev<unsafe>" not in html


def test_html_summary_distinguishes_final_acceptance_from_an_identical_conditional_gate():
    current, previous = acceptance_comparison_states(previous=False, current=True)
    for state, recorded in ((previous, "No"), (current, "Yes")):
        assert state.bundle.gate.verdict is GateVerdict.CONDITIONAL
        overview = export_html(state).split("<h2>Criteria Source</h2>", 1)[0]
        assert "<strong>Review status:</strong> Accepted with exceptions" in overview
        assert f"<strong>Recorded final acceptance:</strong> {recorded}" in overview
