# ScopeProof Stage 2A Durability Design

**Date:** 2026-07-11

**Status:** Approved through the persistent ScopeProof goal contract

## Objective

Make the public-repository MVP truthful and durable before expanding distribution. The immediate priority is to replace benchmark coverage declarations with executable, labeled fixtures and to keep every finding, decision, export, and gate auditable after a review is reopened.

## Non-negotiable boundaries

- No paid LLM, hosted model API, or model-generated verdict.
- Public repositories and local fixtures remain first-class.
- The optional GitHub token is session-only and never written to local review records, logs, or exports.
- ScopeProof never executes pull-request code.
- Candidate implementation evidence remains E1; candidate test evidence remains E2 until a human confirms it; runtime evidence stays manual.
- Partial ingestion, missing required checks, unresolved ambiguity, retrieval failures, or unconfirmed criteria cannot produce Ready.
- Generic bug detection, security review, style review, auto-fixes, hosted accounts, and private-repository storage remain out of scope.

## Delivery sequence

### 1. Executable benchmark truth

The existing benchmark must stop equating a declared category list with executed coverage. Each required category becomes an independently runnable fixture bundle with:

- PR-shaped source snapshot;
- source requirements and confirmed criteria;
- expected evidence IDs or evidence absence;
- expected finding status and gate;
- acceptable alternative evidence;
- a human-review requirement flag;
- a case identifier and category.

The runner loads every label file, executes the same retrieval, verification, and gate path used by the product, and reports actual case and criterion counts. It distinguishes mismatches, evidence-link errors, must-have False Ready, False Blocker, and unexecuted declarations.

### 2. Review lifecycle

Criteria become an immutable-audit lifecycle instead of mutable UI rows. Editing criteria after confirmation creates a new confirmed criteria revision and invalidates the existing provisional analysis. Human resolutions are append-only audit events; the current decision is derived from the latest event per criterion. Final acceptance is a distinct review-level event.

### 3. Local persistence

The first persistence backend is versioned JSON stored only in a user-selected local directory. A review record contains the validated ReviewBundle plus lifecycle metadata; it excludes any credential. Load validates schema and format version. A changed head SHA is detected by comparing the loaded review to a newly ingested snapshot rather than silently updating old evidence.

### 4. Retrieval and ingestion safety

GitHub ingestion becomes paginated and explicitly bounded. Retrieval may inspect a small, justified set of unchanged files, recording why they were fetched, their head SHA, byte limits, and whether the search was partial. Deleted lines, binary data, missing patches, or skipped pages remain visible as limitations.

### 5. UX and reporting

The Streamlit workbench reads and writes only core lifecycle services. It exposes criteria revisions, resolution history, final acceptance, save/reopen, ingestion warnings, and status filters. Markdown, JSON, CSV, and later HTML rendering consume the same persisted bundle and lifecycle data.

## Data-flow contract

```text
Fixture or GitHub snapshot
       ↓
Confirmed criteria revision
       ↓
Bounded evidence retrieval
       ↓
Provisional findings
       ↓
Append-only human resolution events
       ↓
Deterministic gate
       ↓
Validated local record and consistent exports
```

## Stage 2A acceptance gates

1. Every claimed benchmark case is executed; coverage counts derive from execution, not static metadata.
2. Known must-have False Ready is zero across every fixture.
3. Every benchmark mismatch and bad evidence link is reported with case and criterion context.
4. Criterion edits require reconfirmation and invalidate stale analysis.
5. Resolution history is visible and deterministic.
6. Local save/reopen preserves review identity, SHAs, criteria, evidence, findings, history, and gate without secrets.
7. Partial ingestion and retrieval cannot produce Ready.
8. All exports agree with the live and reopened review.
9. The Streamlit AppTest workflow covers save, reopen, history, and final acceptance.
10. Ruff, all tests, the benchmark, public GitHub smoke, and a Streamlit health smoke pass.

## Explicitly deferred

Stage 2B CLI and dogfooding, Stage 3 GitHub Action, Stage 4 evaluation comparisons and rule packs, Stage 5 privacy-readiness, and Stage 6 manual runtime evidence follow only after the Stage 2A gates pass.
