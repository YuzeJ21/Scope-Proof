# Source-bound typed criteria handoff

## Intent and scope

An authorized requirements owner can prepare explicit normalized intent once and hand it to
a CLI operator without changing criterion IDs, order, priority, type, origin, source span, or
required evidence level. Current CLI preparation/review reconstruct only sequential IDs and
text, so a confirmation for customized workbench criteria correctly fails rather than silently
using E1 defaults. This change supplies a supported input path; it does not infer approval.

The owner delegated routine design and automatic execution. The choices below are engineering
judgments, not user-tested requirements or evidence of market demand.

## Approaches

1. Keep text-only input and document its defaults: small, but leaves the handoff interruption.
2. Add a source-bound normalized document shared by preparation, validation and review: selected
   because the existing complete criterion digest and provenance already support these fields.
3. Import complete saved reviews: useful for recipient continuation, but involves independent
   collision, migration, identity and storage contracts; defer to a separately bounded slice.

## Contract

- New pure-core `NormalizedCriteriaDocument` in `scopeproof_core/criteria/document.py` contains
  `schema_version: Literal[1]`, `source_text_sha256` (64 lowercase hex characters), and a nonempty
  ordered `list[Criterion]`. Unknown fields, duplicate IDs and invalid criteria are rejected.
  Existing Criterion normalization/defaults apply; the emitted draft makes every field visible.
- `prepare-criteria --requirements PATH --output PATH` produces an **unconfirmed** document from
  the existing line parser. It does not produce provenance, assert an actor, or enable analysis.
  The output is an editable intent snapshot, not evidence or approval. Reject an oversized
  generated draft before writing it, so every emitted draft fits the same 1 MiB read budget.
- Optional `--criteria PATH` on `prepare-requirements-confirmation`,
  `validate-requirements-confirmation`, and `review` selects this document. One shared reader
  validates a bounded regular file (at most 1 MiB) and exact source-text hash, retaining complete
  ordered Criterion fields. Never fall back to the line parser after a typed-input error.
- Source is exact UTF-8 bytes, including CRLF and non-ASCII. Edited/split normalized criteria may
  differ from original source lines, as in the existing workbench; explicit confirmation binds
  both the original source and the selected complete normalized intent. No semantic equivalence
  is inferred. Changing either after confirmation invalidates it. Empty/whitespace original
  source is rejected before confirmation or ingestion, matching existing owning-source rules.
- Existing confirmation schema and explicit `--confirmed-by` attestation remain. The preparer
  must inspect the complete normalized document before attesting. Identity/authority remain
  asserted, not authenticated. Automated fixtures use clearly CONSTRUCTED actors only.
- Validate typed input and confirmation before fixture ingestion, network access, or saving a
  review/report. Draft and confirmation output use existing atomic no-overwrite publication.
- Without `--criteria`, exact existing text-only digests and behavior remain unchanged.
- GitHub Action, alpha, workbench editing, gate policy, retrieval, persisted record version 9,
  saved review mutation and package version 0.2.5 stay unchanged. Typed documents do not supply
  test/runtime proof or allow untrusted target code execution.

## Product direction and limits

Position the product around explaining and revisiting acceptance decisions. Official-source
research dated 2026-11-02 already shows acceptance validation, traceability and freshness in
other tools; no uniqueness or superiority claim follows. The new input path reduces one concrete
coordination interruption. Actual setup cost, usefulness, buyer and repeat use remain unknown.

Stage 2 remains owner-led productization. Next distinct option is safe portable review transfer,
subject to its own design. Publishing an updated evaluation release needs separate authorization;
Stage 3 requires genuine independent-use evidence and separate authorization. No personal testing,
qualifying-review request, release, deployment, outreach or commercial offer is part of this goal.

## Verification

Watch draft/full-field handoff tests fail against unchanged source. Prove prepare → explicit
confirmation → validate → fixture review → save → JSON/readable export with nonconsecutive IDs,
E3/E4, should-have priority, ordering and source metadata. Mutate each field, order and source;
reject before ingestion/writes. Cover empty/duplicate/unknown/malformed/oversized input and
no-overwrite output, and preserve plain-text hashes. Run a constructed installed-wheel journey
outside the checkout. Run the full suite at its unchanged 95% unrounded coverage floor, lint,
lock validation, deterministic benchmarks, installed browser suite, and hosted Python/Windows
compatibility. Freeze R-002 bytes. Obtain one independent whole-branch agent review, resolve
supported findings, require exact-head CI, merge with expected-head binding, and verify main.
