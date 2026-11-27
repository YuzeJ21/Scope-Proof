# Compare supplied CI context for one reviewed commit

## Goal and authorization

The owner requested a fresh project review and execution of the next roadmap
priority. The prior P0/P1/P2 engineering outcomes are implemented in PRs #304/#305.
Independent use remains gated. This new bounded Stage 2 outcome addresses the
existing evaluation guide's manual before/after snapshot comparison.

A reviewer supplies two CI manifests for the same saved, confirmed review and
receives one offline report explaining changed effective results, mappings, and run
records. For the existing B rehearsal, row access changes from skipped to failed;
filter failure and header pass retain their initial-B citations. The saved review,
its acceptance decisions and deterministic gate remain untouched.

## Approach

Extend `ci-snapshot` with explicit `--previous-manifest PATH`. Omission keeps the
existing snapshot behavior. Use a UI-independent Pydantic comparison model backed
by the existing manifest parser, context validation and status projection. Render a
separate offline HTML comparison. A new CLI command would duplicate the existing
export path; workbench history/storage would add unnecessary application state.

This implements a complete scripted handoff, not a new stored-review format.
Workbench integration is a later separately bounded priority.

## Acceptance criteria

1. Both bounded manifests match the same saved review, confirmed criteria and full
   reviewed SHA. Refuse pending reviews, mismatches and existing output paths.
2. Show each test once, with previous/current mapping, effective status and supplying
   run IDs. Distinguish added/removed mappings and changed effective/source context.
3. Show introduced, removed, modified and retained run records, including their
   head, URL and reported outcomes. Reused run IDs with different data are modified
   assertions, not silently retained evidence.
4. A result can be retained while another run is introduced. Explicit skips in a
   targeted run do not erase earlier exact-build pass/fail reports under existing
   projection rules. Conflicting pass/fail remains unknown.
5. Previous/current mean supplied file order, not verified chronology. All results
   are externally supplied and unauthenticated; no target tests are executed.
6. Record both manifest SHA-256 values, review/criteria identity and the unchanged
   recorded gate. Validate exported objects with strict Pydantic schemas. Revalidate
   before rendering, retain immutable input bytes and derive digests from those bytes.
   Reject parsed fields that drift semantically from their original bytes.
7. HTML is self-contained with readable desktop/phone tables, keyboard scrolling,
   links to cited runs, no scripts and zero automatic network requests.

## Boundaries

No evidence-rule or gate change, cross-head inference, automatic acceptance,
record migration, private access, connector, new dependency, release, deployment,
outreach or independent-use claim. Preserve PR #305's frozen example and R-002.
Sync a reviewed follow-on PR based on #305; leave integration/publication separate.
