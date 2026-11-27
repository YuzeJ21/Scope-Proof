"""Self-contained HTML for a read-only comparison of externally supplied CI context."""

from __future__ import annotations

from html import escape

from scopeproof_core.presentation import review_status_label
from scopeproof_core.reviews.ci_comparison import (
    CI_COMPARISON_BOUNDARY,
    CIStatusComparison,
    CITestComparison,
)
from scopeproof_core.reviews.ci_status import CI_STATUS_LABELS, CIStatusRun, CITestStatus

_TEST_CHANGES = {
    "added": "New test mapping",
    "removed": "Test no longer mapped",
    "changed": "Changed status, mapping or cited run context",
    "unchanged": "Retained effective result",
}
_RUN_CHANGES = {
    "added": "Introduced in current manifest",
    "removed": "Absent from current manifest",
    "changed": "Changed supplied record",
    "unchanged": "Retained supplied record",
}


def _test_status(test: CITestStatus | None) -> str:
    if test is None:
        return "Not mapped"
    return f"{CI_STATUS_LABELS[test.status]}<br><small>{escape(test.reason)}</small>"


def _test_sources(test: CITestStatus | None, side: str, numbers: dict[str, int]) -> str:
    if test is None or not test.run_ids:
        return "None supplied"
    return ", ".join(
        f'<a href="#{side}-run-{numbers[run_id]}">{escape(run_id)}</a>'
        for run_id in test.run_ids
    )


def _test_row(row: CITestComparison, numbers: dict[str, int]) -> str:
    return (
        f'<tr data-test-id="{escape(row.test_id)}"><th scope="row"><code>'
        f"{escape(row.test_id)}</code></th>"
        f"<td>{escape(', '.join(row.previous_criterion_ids)) or 'None'}</td>"
        f"<td>{_test_status(row.previous)}</td>"
        f"<td>{_test_sources(row.previous, 'previous', numbers)}</td>"
        f"<td>{escape(', '.join(row.current_criterion_ids)) or 'None'}</td>"
        f"<td>{_test_status(row.current)}</td>"
        f"<td>{_test_sources(row.current, 'current', numbers)}</td>"
        f"<td>{_TEST_CHANGES[row.change]}</td></tr>"
    )


def _run_record(run: CIStatusRun | None, side: str, number: int) -> str:
    if run is None:
        return "No supplied record"
    outcomes = "".join(
        f"<li><code>{escape(test_id)}</code>: {CI_STATUS_LABELS[outcome]}</li>"
        for test_id, outcome in sorted(run.outcomes.items())
    )
    return (
        f'<div id="{side}-run-{number}"><p>Reported commit <code>{run.head_sha}</code></p>'
        f'<p><a href="{escape(run.source_url, quote=True)}">{escape(run.source_url)}</a></p>'
        + (f"<ul>{outcomes}</ul>" if outcomes else "<p>No outcome supplied in this run.</p>")
        + "</div>"
    )


def export_ci_comparison_html(comparison: CIStatusComparison) -> str:
    """Revalidate inputs and derive every displayed row; never update the saved review."""
    comparison = CIStatusComparison.model_validate(comparison.model_dump(mode="python"))
    previous, current = comparison.previous_snapshot, comparison.current_snapshot
    rows, runs = comparison.test_changes(), comparison.run_changes()
    run_numbers = {run.run_id: number for number, run in enumerate(runs, 1)}
    changed = sum(row.change != "unchanged" for row in rows)
    review = comparison.bundle.review
    metadata = (
        ("Review ID", review.review_id),
        ("Repository", review.repository),
        ("Pull request", f"#{review.pr_number}"),
        ("Reviewed commit", review.head_sha),
        ("Confirmed criteria SHA-256", current.criteria_sha256),
        ("Previous supplied manifest SHA-256", comparison.previous_sha256),
        ("Current supplied manifest SHA-256", comparison.current_sha256),
    )
    lines = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>ScopeProof CI Context Comparison</title><style>",
        "*{box-sizing:border-box}body{font:1rem/1.55 system-ui,sans-serif;margin:0;"
        "color:#172b3a;overflow-wrap:anywhere}main{max-width:78rem;margin:auto;padding:1.25rem}"
        "section{margin:2rem 0}h1{line-height:1.2}dt{font-weight:650}dd{margin:0 0 .6rem}"
        "code{overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}"
        "td,th{border:1px solid #abbac4;padding:.5rem;text-align:left;vertical-align:top}"
        ".table-scroll{overflow-x:auto}.test-table{min-width:65rem}.run-table{min-width:52rem}"
        "a{color:#12516c}a:focus-visible,.table-scroll:focus-visible{outline:3px solid #ad4d0a}"
        ".boundary{border:2px solid #a65813;padding:1rem}small{font-size:.85rem}"
        "</style></head><body><main><h1>ScopeProof CI Context Comparison</h1>",
        f'<p class="boundary">{CI_COMPARISON_BOUNDARY}</p><dl>',
        *[f"<dt>{label}</dt><dd><code>{escape(value)}</code></dd>" for label, value in metadata],
        "</dl><section><h2>What changed in the supplied context</h2>",
        "<p>Test rows with changed status, mapping or cited context: "
        f"<strong>{changed}</strong>.</p>",
    ]
    if not changed:
        lines.append(
            "<p>No changes to effective test rows. Supplied run records may differ below.</p>"
        )
    lines.extend([
        "<p>A changed row can reflect a mapping or source-record change with the same CI status. "
        "It does not establish a regression or fix. An explicit skip in another run does not erase "
        "an earlier pass or failure for the same reviewed commit "
        "under the existing projection.</p>",
        '<div class="table-scroll" role="region" tabindex="0" aria-label="CI result comparison">',
        '<table class="test-table" aria-label="CI test changes"><thead><tr>',
        '<th scope="col">Expected test</th><th scope="col">Previous criteria</th>',
        '<th scope="col">Previous effective CI</th><th scope="col">Previous sources</th>',
        '<th scope="col">Current criteria</th><th scope="col">Current effective CI</th>',
        '<th scope="col">Current sources</th><th scope="col">Comparison</th>',
        "</tr></thead><tbody>",
        *[_test_row(row, run_numbers) for row in rows],
        "</tbody></table></div></section><section><h2>Confirmed criteria and mapping gaps</h2><ul>",
        *[f"<li><code>{escape(row.criterion_id)}</code>: {escape(row.criterion_text)}</li>"
          for row in current.criteria],
        "</ul>",
    ])
    for label, snapshot in (("Previous", previous), ("Current", current)):
        unmapped = ", ".join(row.criterion_id for row in snapshot.criteria if not row.tests)
        lines.append(
            f"<p>{label} criteria without a supplied test mapping: {unmapped or 'None'}.</p>"
        )
    unresolved = [row.test_id for row in rows if row.current and row.current.status != "passed"]
    lines.append("<h3>What to check next</h3>")
    if unresolved:
        lines.append(
            "<p>Inspect the current supplied results and cited runs for "
            + escape(", ".join(unresolved)) + ". Resolve missing mappings separately.</p>"
        )
    else:
        lines.append(
            "<p>All mapped current tests report a pass. Check any unmapped criteria and the "
            "saved review's evidence, scope and acceptance requirements separately.</p>"
        )
    lines.extend([
        "</section><section><h2>Supplied run records</h2>",
        "<p>Introduced and absent refer to these two files, not execution time. A reused run ID "
        "with different reported data is a changed assertion. Each record retains its own "
        "reported commit, reference and outcomes.</p>",
        '<div class="table-scroll" role="region" tabindex="0" aria-label="CI run comparison">',
        '<table class="run-table" aria-label="Supplied CI run records"><thead><tr>',
        '<th scope="col">Run ID</th><th scope="col">Record comparison</th>',
        '<th scope="col">Previous supplied record</th><th scope="col">Current supplied record</th>',
        "</tr></thead><tbody>",
    ])
    for run in runs:
        number = run_numbers[run.run_id]
        lines.append(
            f'<tr><th scope="row"><code>{escape(run.run_id)}</code></th>'
            f"<td>{_RUN_CHANGES[run.change]}</td>"
            f"<td>{_run_record(run.previous, 'previous', number)}</td>"
            f"<td>{_run_record(run.current, 'current', number)}</td></tr>"
        )
    lines.extend([
        "</tbody></table></div></section><section><h2>Saved acceptance record</h2>",
        "<p>This comparison does not apply these external results to the recorded acceptance gate. "
        "A recorded review status is not a new assessment of the supplied CI context.</p>",
        "<p>Recorded review status (unchanged): <strong>"
        + review_status_label(comparison.bundle.gate.verdict) + "</strong>.</p>",
        "<p>Recorded final acceptance (unchanged): <strong>"
        + ("Yes" if review.final_acceptance else "No") + "</strong>.</p>",
        "</section></main></body></html>",
    ])
    return "\n".join(lines) + "\n"
