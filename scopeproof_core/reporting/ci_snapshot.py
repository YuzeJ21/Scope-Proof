"""Standalone HTML for externally supplied CI status for one reviewed build."""

from __future__ import annotations

from html import escape
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scopeproof_core.reviews.ci_status import (
    CI_STATUS_LABELS,
    EXACT_HEAD_PATTERN,
    CIFollowUpSummary,
    CIStatusManifest,
    CIStatusRunReference,
    CITestStatus,
    CriterionCIStatus,
    criterion_ci_statuses,
    summarize_ci_follow_up,
)
from scopeproof_core.schemas.models import (
    GITHUB_REPOSITORY_PATTERN,
    ReviewBundle,
)

CIStatusSnapshotSource = Literal["manual-upload", "configured-local", "local-file"]
_SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
_SOURCE_LABELS = {
    "manual-upload": "Manual upload",
    "configured-local": "Configured local folder",
    "local-file": "Local file",
}
_TITLE = "ScopeProof CI Status Snapshot"
_EVIDENCE_BOUNDARY = (
    "Externally supplied CI results. ScopeProof does not authenticate the manifest "
    "or run the tests. This snapshot does not record an acceptance decision."
)


class CIStatusSnapshotCriterion(CriterionCIStatus):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    criterion_text: str = Field(min_length=1)


class CIStatusSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    review_id: str = Field(min_length=1)
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: int = Field(gt=0)
    reviewed_head_sha: str = Field(pattern=EXACT_HEAD_PATTERN)
    criteria_revision_number: Annotated[int, Field(gt=0)] | Literal["unknown"]
    criteria_sha256: _SHA256
    manifest_sha256: _SHA256
    source: CIStatusSnapshotSource
    criteria: tuple[CIStatusSnapshotCriterion, ...]
    cited_runs: tuple[CIStatusRunReference, ...]

    @model_validator(mode="after")
    def validate_run_citations(self) -> CIStatusSnapshot:
        referenced = {
            run_id
            for criterion in self.criteria
            for test in criterion.tests
            for run_id in test.run_ids
        }
        included = {run.run_id for run in self.cited_runs}
        if referenced != included or len(included) != len(self.cited_runs):
            raise ValueError("snapshot must include each cited CI run exactly once")
        return self


def build_ci_status_snapshot(
    bundle: ReviewBundle,
    manifest: CIStatusManifest,
    *,
    manifest_sha256: str,
    source: CIStatusSnapshotSource,
) -> CIStatusSnapshot:
    """Project a validated manifest without changing the recorded review."""
    statuses = criterion_ci_statuses(bundle, manifest)
    review = bundle.review
    if not any(run.head_sha == review.head_sha for run in manifest.runs):
        raise ValueError("CI status snapshot requires an exact-head run")

    cited_ids = {run_id for status in statuses for test in status.tests for run_id in test.run_ids}
    return CIStatusSnapshot(
        review_id=review.review_id,
        repository=review.repository,
        pr_number=review.pr_number,
        reviewed_head_sha=review.head_sha,
        criteria_revision_number=bundle.criteria_revision_number,
        criteria_sha256=manifest.criteria_sha256,
        manifest_sha256=manifest_sha256,
        source=source,
        criteria=tuple(
            CIStatusSnapshotCriterion(
                criterion_id=status.criterion_id,
                criterion_text=criterion.text,
                status=status.status,
                tests=status.tests,
            )
            for criterion, status in zip(bundle.criteria, statuses, strict=True)
        ),
        cited_runs=tuple(
            CIStatusRunReference(
                run_id=run.run_id, head_sha=run.head_sha, source_url=run.source_url,
            )
            for run in sorted(manifest.runs, key=lambda run: run.run_id)
            if run.run_id in cited_ids
        ),
    )


def _test_run_links(test: CITestStatus, run_numbers: dict[str, int]) -> str:
    return ", ".join(
        f'<a href="#ci-run-{run_numbers[run_id]}">[{run_numbers[run_id]}]</a>'
        for run_id in test.run_ids
    ) or "None"


def _follow_up_html(follow_up: CIFollowUpSummary, run_numbers: dict[str, int]) -> list[str]:
    lines = ['<section aria-labelledby="ci-follow-up"><h2 id="ci-follow-up">CI follow-up</h2>']
    if follow_up.tests:
        lines.extend([
            '<table aria-label="CI tests needing follow-up">',
            '<thead><tr><th scope="col">Expected test</th><th scope="col">Mapped criteria</th>',
            '<th scope="col">CI status</th><th scope="col">Why</th>',
            '<th scope="col">CI runs</th></tr></thead><tbody>',
        ])
        for test in follow_up.tests:
            criteria = escape(", ".join(test.criterion_ids))
            lines.append(
                f"<tr><td><code>{escape(test.test_id)}</code></td><td>{criteria}</td>"
                f"<td>{CI_STATUS_LABELS[test.status]}</td><td>{escape(test.reason)}</td>"
                f"<td>{_test_run_links(test, run_numbers)}</td></tr>"
            )
        lines.append("</tbody></table>")
    else:
        lines.append("<p>All mapped CI tests reported a pass for this commit.</p>")
    if follow_up.unmapped_criterion_ids:
        criteria = escape(", ".join(follow_up.unmapped_criterion_ids))
        lines.append(f"<p>No CI tests are mapped to {criteria}.</p>")
    lines.append("</section>")
    return lines


def _criterion_html(
    criterion: CIStatusSnapshotCriterion, number: int, run_numbers: dict[str, int],
) -> list[str]:
    heading = f"criterion-{number}"
    lines = [
        f'<section aria-labelledby="{heading}">',
        f'<h2 id="{heading}">{escape(criterion.criterion_id)}</h2>',
        f'<p class="criterion-text">{escape(criterion.criterion_text)}</p>',
        f"<p>CI status <strong>{CI_STATUS_LABELS[criterion.status]}</strong></p>",
    ]
    if not criterion.tests:
        lines.extend([
            "<p>The manifest does not identify expected tests for this criterion.</p>",
            "</section>",
        ])
        return lines
    lines.extend([
        '<table aria-label="Expected CI tests">',
        '<thead><tr><th scope="col">Expected test</th><th scope="col">CI status</th>',
        '<th scope="col">Why</th><th scope="col">CI runs</th></tr></thead><tbody>',
    ])
    for test in criterion.tests:
        lines.append(
            f"<tr><td><code>{escape(test.test_id)}</code></td>"
            f"<td>{CI_STATUS_LABELS[test.status]}</td>"
            f"<td>{escape(test.reason)}</td><td>{_test_run_links(test, run_numbers)}</td></tr>"
        )
    lines.extend(["</tbody></table>", "</section>"])
    return lines


def export_ci_status_snapshot_html(snapshot: CIStatusSnapshot) -> str:
    """Render a validated offline snapshot with no automatically loaded resources."""
    snapshot = CIStatusSnapshot.model_validate(snapshot.model_dump())
    metadata = (
        ("Review ID", snapshot.review_id),
        ("Repository", snapshot.repository),
        ("Pull request", f"#{snapshot.pr_number}"),
        ("Reviewed commit", snapshot.reviewed_head_sha),
        ("Confirmed criteria revision", str(snapshot.criteria_revision_number)),
        ("Confirmed criteria SHA-256", snapshot.criteria_sha256),
        ("CI manifest SHA-256", snapshot.manifest_sha256),
        ("Manifest source", _SOURCE_LABELS[snapshot.source]),
    )
    lines = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_TITLE}</title>",
        "<style>body{font:1rem/1.55 system-ui,sans-serif;max-width:70rem;margin:auto;"
        "padding:1.25rem;overflow-wrap:anywhere}section{margin:2rem 0}"
        "table{width:100%;border-collapse:collapse}td,th{border:1px solid gray;"
        "padding:.4rem;text-align:left;vertical-align:top}"
        "dt{font-weight:700}dd{margin:0 0 .5rem}"
        ".criterion-text{white-space:pre-wrap}</style>",
        "</head><body><main>",
        f"<h1>{_TITLE}</h1><p>{_EVIDENCE_BOUNDARY}</p>",
        "<dl>",
        *(f"<dt>{label}</dt><dd>{escape(value)}</dd>" for label, value in metadata),
        "</dl>",
    ]
    run_numbers = {run.run_id: index for index, run in enumerate(snapshot.cited_runs, 1)}
    lines.extend(_follow_up_html(summarize_ci_follow_up(snapshot.criteria), run_numbers))
    for index, criterion in enumerate(snapshot.criteria, 1):
        lines.extend(_criterion_html(criterion, index, run_numbers))
    lines.append('<section aria-labelledby="cited-runs"><h2 id="cited-runs">Cited CI runs</h2>')
    if snapshot.cited_runs:
        lines.append("<ol>")
        for index, run in enumerate(snapshot.cited_runs, 1):
            url = escape(run.source_url)
            lines.append(
                f'<li id="ci-run-{index}"><strong>{escape(run.run_id)}</strong> '
                f'· Commit <code>{escape(run.head_sha)}</code> · <a href="{url}">{url}</a></li>'
            )
        lines.append("</ol>")
    else:
        lines.append("<p>No CI runs are cited by the displayed results.</p>")
    lines.extend(["</section>", "</main></body></html>"])
    return "\n".join(lines)
