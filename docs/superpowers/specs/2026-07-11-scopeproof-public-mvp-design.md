# ScopeProof Public Repository MVP Design

**Date:** 2026-07-11

**Status:** Approved design

**Product:** ScopeProof — *Prove the PR matches the product intent.*

## 1. Objective

Build a zero-paid-LLM public-repository MVP that helps product managers, technical founders, QA leads, and small AI-assisted development teams review whether a GitHub pull request satisfies user-confirmed acceptance criteria.

The MVP converts each confirmed criterion into an auditable requirement-to-evidence record. It retrieves candidate implementation, test, CI, and documentation evidence using deterministic rules; exposes missing or partial coverage; requires human resolution where the evidence is insufficient; and produces a reproducible release recommendation.

ScopeProof is an evidence assistant, not a correctness oracle. It does not replace engineering review or QA.

## 2. Success Criteria

The MVP succeeds when a user can:

1. Enter a public GitHub pull-request URL without requiring a token.
2. Optionally provide a GitHub token for increased free rate limits without the token being persisted.
3. Paste, split, edit, prioritize, and confirm atomic acceptance criteria.
4. Retrieve auditable candidate evidence for each confirmed criterion.
5. Review Missing, Partial, and Needs Review findings without any weak match being presented as proof.
6. Resolve findings through explicit human decisions.
7. Receive a deterministic Ready, Conditional, Blocked, or Needs Review recommendation.
8. Export the review as Markdown, JSON, and CSV.
9. Complete an offline demo flow using bundled fixtures.

The internal product metric is confirmed acceptance gaps found before merge. The first release must track False Ready separately and treat a known must-have False Ready as release-blocking.

## 3. Scope

### 3.1 Included

- Public GitHub pull requests.
- Anonymous GitHub access with an optional session-only token.
- PR metadata, changed files, patches, commits, and check status.
- User-authored and user-confirmed atomic criteria.
- Must-have and should-have priorities.
- Deterministic evidence retrieval.
- Evidence matrix and criterion detail views.
- Human confirmation, rejection, manual verification, accepted exception, and change-required decisions.
- Deterministic gate evaluation.
- Markdown, JSON, and CSV exports.
- Bundled demo fixtures and a regression benchmark.
- Local-first Streamlit application with a UI-independent Python core.

### 3.2 Excluded

- OpenAI, hosted LLM, or other paid model APIs.
- Automatic semantic requirement generation.
- Private repositories.
- Jira, Linear, billing, accounts, teams, or permissions.
- General code review, bug detection, vulnerability scanning, or style review.
- Automatic fixes.
- Execution of pull-request code.
- Automated browser or runtime verification.
- A hosted database, long-term token storage, or remote code retention.
- GitHub Actions integration in the first release.

### 3.3 Future-Compatible Boundaries

The core engine will expose interfaces that can later support a CLI, GitHub Action, local model adapter, private-repository connector, or runtime evidence provider. None of those extensions may be required by the MVP.

## 4. Product Principles

1. Every criterion verdict cites explicit evidence or explicitly states what evidence is missing.
2. Finding related code is not verification.
3. Implementation evidence is never presented as test or runtime evidence.
4. GitHub checks passing does not prove requirement coverage.
5. Users must confirm criteria before analysis begins.
6. Suggested implicit criteria, if added later, remain separate from source requirements.
7. False Ready is more harmful than False Blocked.
8. Weak or conflicting evidence produces Needs Review.
9. Gate decisions are deterministic and reproducible.
10. Untrusted repository code is never executed by the application.

## 5. Architecture

The application uses a Python core with a Streamlit presentation layer:

```text
Public GitHub PR
      ↓
GitHub ingestion
      ↓
User-authored and confirmed criteria
      ↓
Deterministic evidence retrieval
      ↓
Evidence matrix
      ↓
Human resolution
      ↓
Deterministic gate evaluation
      ↓
Markdown / JSON / CSV export
```

Proposed repository boundaries:

```text
scopeproof/
├── apps/
│   └── web/                  # Streamlit presentation layer
├── scopeproof_core/
│   ├── github/              # Public PR ingestion
│   ├── criteria/            # Criterion parsing and validation helpers
│   ├── retrieval/           # Deterministic candidate-evidence rules
│   ├── verification/        # Criterion status calculation
│   ├── gates/               # Release recommendation truth table
│   ├── reporting/           # Markdown, JSON, and CSV rendering
│   └── schemas/             # Pydantic domain models
├── evals/
│   ├── fixtures/
│   ├── labels/
│   └── regression/
├── tests/
├── docs/
└── AGENTS.md
```

The core must not import Streamlit. UI state is translated into validated core schemas at the application boundary.

## 6. Components

### 6.1 GitHub Ingestion

Responsibilities:

- Validate and normalize a GitHub pull-request URL.
- Fetch PR title, description, repository identity, base SHA, head SHA, commits, changed files, patches, and available check status.
- Construct stable GitHub permalinks anchored to the head SHA.
- Distinguish invalid URLs, nonexistent PRs, private/inaccessible repositories, rate limits, network errors, and oversized diffs.
- Support anonymous access and an optional token held only in Streamlit session memory.

The ingestion layer must expose partial-result warnings. It must never silently treat truncated data as complete.

### 6.2 Criterion Preparation

Because the MVP has no LLM, the user remains responsible for the meaning of the criteria. The application provides structured entry and lightweight formatting support:

- One independently judgeable behavior per criterion.
- Stable IDs such as `AC-01`.
- Must-have or should-have priority.
- Criterion type such as behavior, error state, analytics, permission, documentation, migration, or non-functional.
- Required evidence level.
- Validation warnings for empty, duplicate, overly long, or visibly compound criteria.

No review may start until the user explicitly confirms the criterion set.

### 6.3 Deterministic Evidence Retrieval

The retrieval engine evaluates explainable signals rather than semantic model output:

- Explicit identifiers, event names, field names, routes, and quoted terms in a criterion.
- Normalized criterion keywords with conservative stop-word removal.
- Changed-file paths and language-aware file classification.
- Added, modified, and deleted diff lines.
- Test-file paths, test names, assertions, and nearby text.
- Documentation, migration, analytics, authorization, error-state, loading-state, and empty-state patterns.
- GitHub check status as CI evidence only.

Every candidate evidence item records:

- Evidence type.
- File path and line span.
- Head commit SHA.
- GitHub permalink.
- Short excerpt.
- Matching rule and relevance reason.
- Deterministic relevance score.
- Limitations and missing evidence.

Deleted lines cannot count as current implementation evidence. File existence alone cannot establish test coverage. Candidate scores support ordering but do not independently prove a criterion.

### 6.4 Criterion Verification

The verification layer derives a provisional status from validated evidence and explicit rules. It never hides uncertainty.

Provisional statuses:

- `evidence_found`: candidate evidence exists but has not established full coverage.
- `partial`: evidence addresses only part of the criterion or is below the required level.
- `missing`: the required evidence was not found.
- `needs_review`: the criterion is ambiguous, evidence conflicts, retrieval was incomplete, or the rules cannot judge reliably.

Human-resolved outcomes:

- `accepted`: the reviewer accepts the criterion as satisfied.
- `accepted_exception`: the reviewer knowingly accepts a documented gap.
- `change_required`: the reviewer agrees that a change is required.
- `rejected_finding`: the reviewer rejects the system finding and may attach a note or evidence URL.
- `manually_verified`: the reviewer records external verification, including the claimed evidence level and a note.
- `not_in_scope`: the reviewer explicitly removes the item from the current review scope without deleting its audit record.

### 6.5 Gate Evaluation

The gate evaluator consumes confirmed criteria, criterion findings, human resolutions, CI state, ingestion completeness, and accepted scope exceptions.

`Ready` requires all of the following:

- The criterion set is confirmed.
- All must-have criteria meet their required evidence level or have an explicit accepted human resolution.
- Required GitHub checks are green.
- No unresolved Missing, Partial, or Needs Review item remains.
- Ingestion completed without a material partial-analysis warning.
- The user records final acceptance.

`Conditional` applies when must-have criteria are resolved but only should-have gaps, documented exceptions, or non-blocking runtime confirmations remain.

`Blocked` applies when a must-have is Missing or Partial, a required check fails, a reviewer marks change required, or the evidence explicitly contradicts a criterion.

`Needs Review` applies when criteria are unconfirmed, checks are unavailable where required, ingestion is materially incomplete, evidence is ambiguous or conflicting, or required human decisions remain open.

Precedence is `Blocked` → `Needs Review` → `Conditional` → `Ready`. A lower-confidence state cannot override a blocker.

### 6.6 Reporting

The evidence matrix displays criterion, priority, provisional status, evidence level, confidence band, evidence count, concern, and human resolution. Criterion details expose the permalink, excerpt, matching rationale, limitations, missing evidence, and recommended next action.

Exports contain the review identity, repository, PR number, head SHA, criterion source, evidence, findings, resolutions, gate decision, tool version, rule-set version, and generation timestamp. Secrets and tokens are excluded.

## 7. Evidence Levels

| Level | Meaning | MVP source |
|---|---|---|
| E0 | No evidence | Deterministic absence after a complete retrieval pass |
| E1 | Candidate implementation evidence | Code or contract evidence linked to the criterion |
| E2 | Test evidence | Relevant test evidence explicitly accepted by the reviewer |
| E3 | Runtime evidence | Manually recorded external runtime verification only |
| E4 | Human accepted | Explicit reviewer acceptance decision |

An evidence item has one evidence type. Higher levels do not erase lower-level evidence or its audit trail.

## 8. Core Data Model

### Review

- `review_id`
- `repository`
- `pr_number`
- `base_sha`
- `head_sha`
- `criteria_confirmed`
- `ingestion_status`
- `created_at`
- `tool_version`
- `ruleset_version`

### RequirementSource

- `source_type`
- `source_text`
- `source_url`
- `source_version`

### Criterion

- `criterion_id`
- `review_id`
- `text`
- `priority`
- `criterion_type`
- `source_span`
- `required_evidence_level`

### EvidenceItem

- `evidence_id`
- `criterion_id`
- `evidence_type`
- `file_path`
- `line_start`
- `line_end`
- `commit_sha`
- `permalink`
- `excerpt`
- `matching_rule`
- `relevance_reason`
- `relevance_score`
- `limitations`

### Finding

- `criterion_id`
- `status`
- `confidence_band`
- `reason`
- `missing_evidence`
- `contradictions`
- `recommended_action`

### HumanResolution

- `criterion_id`
- `decision`
- `comment`
- `evidence_url`
- `claimed_evidence_level`
- `reviewer`
- `timestamp`

### GateDecision

- `verdict`
- `blocking_criteria`
- `conditional_criteria`
- `unresolved_criteria`
- `resolved_exceptions`
- `reason_codes`

All persisted and exported objects are validated by Pydantic schemas.

## 9. User Experience

The MVP uses five compact steps in a Streamlit application:

1. **Start Review:** Public PR URL, optional token, requirements input, and bundled demo entry point.
2. **Confirm Criteria:** Add, split, edit, reorder, prioritize, validate, and confirm atomic criteria.
3. **Evidence Matrix:** Review and filter findings by blocker, status, priority, and evidence level.
4. **Criterion Detail:** Inspect evidence, missing evidence, limitations, and record a human resolution.
5. **Summary and Export:** View the reproducible gate decision and export Markdown, JSON, or CSV.

The interface must label deterministic matches as candidate evidence. The UI must keep provisional findings visually distinct from human decisions.

## 10. Error Handling and Privacy

- Invalid GitHub URL: explain the expected PR URL format.
- Missing PR: identify the repository and PR number that could not be found.
- Private or inaccessible repository: state that the MVP supports public repositories only.
- Rate limit: show the reset information when available and offer the optional token field.
- Network failure: retain user-entered criteria and allow retry.
- Large diff: enforce documented file, patch, and total-size limits; list skipped files and force Needs Review when omitted content could affect a criterion.
- Missing checks: represent checks as unavailable, never green.
- Rule or parsing failure: preserve available evidence and force Needs Review.
- Token handling: keep tokens in session memory only; never log, persist, export, or include them in exception messages.
- Local storage: save review JSON locally only when the user explicitly exports or saves it.

## 11. Evaluation and Testing

### 11.1 Test Layers

- Pydantic schema validation tests.
- Gate truth-table unit tests, including precedence and edge cases.
- GitHub response and diff-parser fixture tests.
- Retrieval-rule unit tests with positive and negative evidence.
- Regression tests for evidence ranking and status calculation.
- Markdown, JSON, and CSV output tests.
- Streamlit AppTest coverage for the five-step workflow.
- Live smoke test against a known public PR when network access is available.
- Offline end-to-end test using bundled fixtures.

### 11.2 Benchmark Cases

The bundled benchmark includes:

- Complete implementation.
- Implementation without tests.
- Happy path without an error path.
- Missing user-visible error state.
- Active filter omitted.
- Analytics event omitted.
- Permission change without an authorization test.
- PR description claiming behavior not present in code.
- Test present but checking the wrong behavior.
- Unmapped scope expansion.
- Ambiguous criterion.
- Relevant evidence in an unchanged file, represented as unavailable to the diff-only MVP unless explicitly supplied by GitHub metadata or the user.

Each fixture records expected status, expected evidence, expected gate, acceptable alternative evidence, and whether a human decision is required.

### 11.3 Release Gates

- All automated tests pass.
- Every gate decision is reproducible from exported inputs and ruleset version.
- Every evidence link is anchored to a commit SHA and has a valid file/line target when GitHub provides patch positions.
- Known must-have False Ready cases equal zero in the bundled benchmark.
- False Ready and False Blocker are reported separately.
- The no-token offline demo completes end to end.
- Anonymous public-PR ingestion passes a live smoke test before a release is called runnable.
- README states the product boundaries and does not claim to replace QA or prove correctness.

## 12. Demo Scenario

The bundled launch fixture uses the CSV-export story:

- AC-01: User can export the research list as CSV.
- AC-02: Export respects all active filters.
- AC-03: Failed export displays an error message.
- AC-04: Successful export records `research_exported`.

The controlled PR implements CSV export, one filter, and a happy-path test while omitting another filter, the error state, and analytics. The report must clearly label this as a deliberately constructed demo rather than a real production incident.

## 13. Delivery Sequence

1. Product contracts, schemas, terminology, gate truth table, and repository guidance.
2. Bundled fixtures and gate/retrieval regression harness.
3. Public GitHub ingestion.
4. Criterion preparation and confirmation.
5. Deterministic evidence retrieval and criterion verification.
6. Evidence matrix, human resolution, and summary UI.
7. Markdown, JSON, and CSV exports.
8. Full AppTest, offline demo, live public-PR smoke test, and launch documentation.

This sequence establishes trust contracts and False Ready protection before UI polish.

## 14. Acceptance Criteria for the MVP

1. The application runs locally without any paid API key.
2. A user can complete the bundled demo without network access.
3. A user can ingest a public GitHub PR anonymously or with a session-only optional token.
4. Failures and partial ingestion cannot produce Ready.
5. Analysis cannot begin until the user confirms criteria.
6. Every candidate evidence item includes type, path, SHA, excerpt, rule, rationale, score, and limitations.
7. Deleted lines never count as current implementation evidence.
8. E1 is never presented as E2 or E3.
9. Every criterion has evidence or explicit missing-evidence details.
10. Every gate decision follows the documented deterministic precedence.
11. Human resolutions remain visible in the audit record.
12. Markdown, JSON, and CSV exports agree with the on-screen summary.
13. The benchmark reports False Ready separately and blocks release on any known must-have False Ready.
14. The UI and README state that ScopeProof is an evidence assistant and does not replace QA.

## 15. Open Questions Deferred Beyond the MVP

The following decisions are intentionally deferred and do not block implementation:

- Whether local model adapters materially improve criterion normalization or retrieval.
- Whether private-repository demand justifies GitHub App installation.
- Whether agencies value branded acceptance reports and client sign-off more than product teams value merge gates.
- Whether runtime verification should use Playwright, user-supplied evidence, or a separate isolated runner.
- Whether a future hosted version retains evidence metadata or runs entirely inside customer infrastructure.
