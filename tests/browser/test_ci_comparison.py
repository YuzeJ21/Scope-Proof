"""Read the comparison artifact offline without installing or executing target code."""

import pytest

from scopeproof_core.reporting.ci_comparison import export_ci_comparison_html
from scopeproof_core.reviews.ci_comparison import compare_ci_status
from tests.ci_comparison_fixture import ci_comparison_inputs

pytestmark = pytest.mark.browser


def test_ci_context_comparison_is_readable_offline_and_scrolls_by_keyboard(tmp_path, request):
    if "browser" not in request.config.option.markexpr:
        pytest.skip("run explicitly with -m browser after installing Chromium")
    from playwright.sync_api import expect, sync_playwright

    state, _, _, previous, current = ci_comparison_inputs()
    comparison = compare_ci_status(state.bundle, previous, current)
    report = tmp_path / "comparison.html"
    report.write_text(export_ci_comparison_html(comparison), encoding="utf-8")
    requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for width, height in ((1280, 800), (390, 844)):
                context = browser.new_context(viewport={"width": width, "height": height})
                context.set_offline(True)
                page = context.new_page()
                page.on("request", lambda event: requests.append(event.url)
                        if event.url.startswith(("http:", "https:")) else None)
                page.goto(report.as_uri())
                expect(page.get_by_role("heading", name="ScopeProof CI Context Comparison"))\
                    .to_be_visible()
                assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
                rows = page.get_by_role("table", name="CI test changes").get_by_role("row")
                assert rows.count() == 4
                access = page.locator('tr[data-test-id="row_entitlement"]')
                expect(access.get_by_role("cell", name="Explicitly skipped", exact=False))\
                    .to_have_count(1)
                expect(access.get_by_role("cell", name="Failed", exact=False)).to_have_count(1)
                for anchor in page.locator('a[href^="#"]').all():
                    assert page.locator(anchor.get_attribute("href")).count() == 1
                if width == 390:
                    for name in ("CI result comparison", "CI run comparison"):
                        region = page.get_by_role("region", name=name, exact=True)
                        assert region.evaluate("node => node.scrollWidth > node.clientWidth")
                        region.focus()
                        region.press("ArrowRight")
                        page.wait_for_function("node => node.scrollLeft > 0",
                                               arg=region.element_handle())
                page.screenshot(path=tmp_path / f"comparison-{width}.png", full_page=True)
                context.close()
        finally:
            browser.close()
    assert requests == []
