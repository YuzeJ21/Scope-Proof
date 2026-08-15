# Public-alpha outcome form

Record exactly one outcome after reviewing the evidence and decisions:

- `found_useful_gap` — ScopeProof surfaced a requirement-evidence gap the participant considered useful.
- `showed_only_known_information` — the review was understandable but added no useful new information.
- `created_friction` — qualification, criteria, evidence, decisions, outcome, export, or integration created material friction. Supply `--friction-stage`.

Example:

```bash
scopeproof alpha outcome CASE_ID \
  --review-id REVIEW_ID \
  --review-storage-dir .scopeproof/reviews \
  --result created_friction \
  --friction-stage evidence \
  --notes-file outcome-notes.txt
```

ScopeProof loads and revalidates that saved review, then derives its exact head SHA. The outcome
is rejected unless the review came from live public GitHub ingestion and matches the qualified
public PR, verified-public repository fact, ordered criteria snapshot, and source provenance.
The alpha case itself must preserve the same verified-public fact. Fixture, demo, research, and legacy
or unverified review origins cannot complete genuine alpha evidence; a historical record
without visibility evidence must be re-fetched and reconfirmed rather than silently migrated.

Report consent and quotation consent are independent. Both default to no. Add `--report-consent` only to allow the reduced public summary; add `--quote-consent` only to permit a quotation. The public summary excludes local notes and permission fields.

Do not claim repeat usage, customer value, market demand, or correctness from one outcome.

## Optional external feedback handoff

The validated local outcome remains the authoritative participant-selected result. After it is
recorded, a participant may read the
[public feedback form](https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-feedback.yml)
to record optional external feedback: independently observed timing, decision impact, and voluntary
reuse intent. Timing is attributable only with an independent observer category and a specific
public evidence reference; otherwise record it as `not observed`.

Stage 1 is closed as not pursued, and this feedback does not reopen Stage 1. The
[30-day Design Partner Sprint](../commercialization/design-partner-sprint.md) is an optional
external-research guide. Commercial discovery is separate from owner-led Stage 2 productization and
requires its own owner authorization before use. That issue is not commercial validation by itself
and does not establish customer validation. No paid product or billing is active. Never copy local
notes, private information, or consent fields into the public issue.
