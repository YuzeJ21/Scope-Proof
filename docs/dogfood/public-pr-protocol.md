# ScopeProof Public PR Dogfood Protocol

## Purpose

Use this protocol to collect reproducible product evidence from public pull requests without claiming that a technical run is user validation.

## Record types

| Record type | Requirements source | What it proves | What it must not claim |
|---|---|---|---|
| Constructed demo | Checked-in fixture label | Regression behavior | Real production incident |
| Technical smoke | Public PR title/body, explicitly marked proxy | GitHub ingestion and report generation | User-confirmed acceptance coverage |
| Confirmed dogfood review | User-approved ticket, PRD, or acceptance criteria | A product review workflow | Broad market validation |

## Confirmed dogfood requirements

Start with the participant-facing ten-minute guide at `docs/alpha/participant-quickstart.md` and complete its public PR qualification checklist. The structured `scopeproof alpha` commands are the preferred local record for new cases; the directory format below remains available for existing manual records.

Before running a confirmed dogfood review, create a local directory containing:

```text
dogfood/<review-name>/
├── review-metadata.json
├── requirements.txt
├── decision-log.md
└── exports/
```

`review-metadata.json` must include:

```json
{
  "record_type": "confirmed_dogfood_review",
  "public_pr_url": "https://github.com/owner/repo/pull/123",
  "requirements_source_type": "user_confirmed_ticket",
  "requirements_source_url": "https://example.com/ticket/123",
  "requirements_confirmed_at": "2026-07-11T12:00:00Z",
  "reviewer": "named reviewer or anonymized role"
}
```

Never invent this metadata. If the requirements are only inferred from the PR title or description, set `record_type` to `technical_smoke` and `requirements_source_type` to `pr_proxy_not_confirmed`.

## Procedure

1. Save one atomic user-confirmed criterion per line in `requirements.txt`.
2. Record the public PR URL and initial head SHA in `review-metadata.json`.
3. Run:

   ```bash
   scopeproof review --pr PR_URL --requirements requirements.txt --storage-dir .scopeproof/reviews
   ```

4. Export Markdown and HTML reports using the printed review ID.
5. In `decision-log.md`, record every accepted, rejected, ambiguous, and accepted-exception finding with the reviewer’s reason.
6. If the PR head SHA changes, preserve the old export and run a new review; do not overwrite old evidence.
7. Convert a confirmed case into a benchmark fixture only when its source is public or safely anonymized, its expected result is human-labeled, and its evidence links are reproducible.

## Evidence that is safe to publish

- A deliberately constructed demo labeled as such.
- A technical smoke labeled as a technical smoke.
- A confirmed dogfood report only with permission from the source owner.
- Aggregate counts only when the source records exist and can be audited locally.

## External validation still required

No local implementation can prove repeat usage, willingness to grant private-repository access, customer value, or market demand. Those claims require actual participants and their permission.
