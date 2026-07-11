from scopeproof_core.demo import build_demo_review
from scopeproof_core.reporting.exporters import export_html


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
