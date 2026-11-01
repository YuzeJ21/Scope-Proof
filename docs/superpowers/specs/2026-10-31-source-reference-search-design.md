# Find reviewer-selected references by source content

## Intent and delegated design

After PR #235 the owner delegated one high-value automatic product task, without personal testing
or qualifying reviews. Live main `abee995a224c8caeaf7c8aa07133d6013b484251` and all post-merge checks
are green. Independent gap inspection found that the file/page reference chooser shows only line
numbers until a line is selected. It already holds eligible exact-head source excerpts but makes
reviewers guess coordinates before reading them.

Select content-first source reference selection ahead of CLI history parity or another comparison
projection. Add literal selected-file search and a numbered page preview. Page-only filtering would
still require guessing which page contains a location; repository search would broaden scope beyond
already-ingested eligible source. No retrieval ranking, semantic matching, new fetching, adapters,
automatic selection, criterion inference, target-code execution or correctness claims.

## Core contract

Extend `scopeproof_core/reviews/selected_references.py` with:

- `MAX_REFERENCE_QUERY_CHARS = 200`.
- `SelectableReferenceSearchPage`: frozen, extra-forbid, revalidated Pydantic object containing the
  existing `source: SelectableReferenceSource` (total eligible file count), explicit `query: str`,
  strict nonnegative `page_index` and `matching_line_count`, plus zero to 100 complete ordered
  `SelectableReferenceLine` records. Query is strict text, maximum 200 Unicode characters. Matching
  is the exact query's casefolded literal substring in each excerpt's casefolded text. Whitespace
  is literal; empty query means browse all eligible lines. Regex/glob syntax has no special meaning.
  Preserve original excerpts and physical Git coordinates without normalization or highlights.
- `page_count` is zero for no matches, otherwise ceiling of matching count / 100. Empty results
  are valid only at page zero; out-of-range pages fail. Counts cannot exceed eligible lines.
  Require exactly the selected match window, unique increasing physical line numbers, same source
  identity, validated nested line instances and literal match membership. Model validation alone
  cannot authenticate global source completeness; the builder derives counts from current source.
- `search_reference_page(state, snapshot, *, source_scope, file_path, query='', page_index=0,
  unchanged_files=None)` applies the existing eligibility iterator to only the explicit selected
  file. Count all eligible and matching lines while retaining at most 100 result records. Unknown,
  excluded or no-longer-eligible sources fail closed; no fallback. Existing browse APIs, source
  exclusions, save-time exact-source/fingerprint/provenance checks and record v7 stay unchanged.

Search reads already-ingested bounded data only. Removed/skipped/truncated/ambiguous files,
duplicate coordinates/paths, wrong-head unchanged candidates, unsupported separator-bearing lines,
empty/oversized lines and other existing exclusions remain excluded. No raw source is reclassified
as runtime verification, automatic candidate evidence or changed-file scope coverage.

## Workbench

Add **Find text in this file (literal, case-insensitive)** after explicit source choice and before
the existing page selector, maximum 200 characters, disabled before source selection. Empty query
browses existing eligible pages. Read the first search page to expose matching and total eligible
counts; the chosen page returns at most 100 matching lines. Label that the scope is eligible loaded
lines in the selected file, not repository-wide or omitted source. No match produces a clear empty
state, disabled page/line controls and no selection fallback.

Show **Source lines on this page (physical Git line numbers)** in inert `st.code(language=None,
wrap_lines=True,height=320)` before the line selector. Prefix each complete raw excerpt with its
actual physical line number. Do not enable artificial display line numbering across source gaps.
The bounded scrollable preview must preserve full text, contain long content, and remain readable
at desktop, 390px phone and CSS 200% zoom. Keep line selector values/names as physical numbers for
compatibility; do not auto-select the first result. The selected excerpt remains separately shown.

Query changes reset page to zero and clear line choice. File changes also clear query; page changes
clear line choice. Existing source/criterion/revision/owner context changes, action changes and
successful save/reset clear query along with reference inputs. Pending queries are drafts, never
persisted in reviews/reports. Add/Correct retain explicit source, line, reviewer and rationale;
Withdraw remains independent of loaded source. Current decisions, automatic findings, confidence,
scope, final acceptance and comparison behavior do not change.

## Verification and finish

Test literal/casefold/whitespace behavior, regex-like text, query bounds/types, no/empty matches,
more than 100 matches and targets beyond the legacy global first 1,000, gaps in physical numbers,
changed and unchanged file scopes, invalid pages/source, all existing exclusions, nested tampering
and unchanged state/source bytes. UI tests must pin reset behavior for query/file/page/source and
no implicit line/decision/save. Browser extends the installed selected-reference journey: browse
existing page 11, search for source text, see the excerpt before selection, verify reset/page counts,
explicitly select/save and reopen. Capture desktop/phone/CSS200 preview geometry and inert hostile
text/long-line preservation. Keep frozen benchmark inputs and expected results unchanged.

Run full suite with actual SysMonitor coverage and existing unrounded 95% floor, lint/lock/diff,
both deterministic benchmarks, clean installed-wheel/browser and available Python/Windows checks.
Independent whole-branch agent review, resolved findings, exact-head hosted checks/CodeQL, guarded
merge and separate resulting-main verification are required. All fixtures/actors are constructed
automation; agent review is not a qualifying practitioner review. Source remains 0.2.5 unreleased,
public v0.2.4 unchanged, Stage 1 closed at zero, Stage 2 owner-led, Stage 3 dormant. No personal
testing, qualifying reviews, release, deployment, outreach or standing feature queue follows.
