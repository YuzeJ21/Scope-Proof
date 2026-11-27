# Workbench CI comparison and integration boundary

The owner requested a next-stage goal prompt and its execution. The bounded goal is to
integrate the reviewed CI handoff work and expose the same comparison in the workbench,
preserving evidence and deferred-download safeguards. The published package stays v0.2.8.

## Change

Comparison is optional. The displayed current manifest and an explicitly uploaded previous
manifest feed the existing strict comparison model and HTML exporter. The workbench shows
effective test results, mappings, supplying runs, run-record changes and both input digests.
There is no separate UI evidence engine, new gate rule, schema migration or dependency.

The configured-source reader now exposes the exact bytes it validated. Existing digest and
model APIs delegate to that bounded no-follow reader. Comparison downloads retain those bytes,
check both upload sources or the configured current file before and after rendering, and
rebuild with the authoritative bundle supplied by the existing deferred review export.
Session retirement revokes older callbacks after input/mode/review changes. Saved-record,
source-conflict and pending-draft authority guards remain in that existing wrapper.

## Verification record

The unchanged #306 tree passed 35 baseline focused checks. Three newline-preservation
regressions failed before the byte-reader interface existed; the complete handoff suite then
passed 20 checks. The first workbench comparison test failed because no comparison controls
existed; all 21 initial cases were observed failing before UI implementation.

The implemented workbench and related core/export/deferred paths passed 85 focused checks.
The tests use actual AppTest uploads and saved records. The byte-drift probe initially mutated
AppTest's separately deserialized upload copy; instrumentation was corrected to retain the
actual objects returned by the real uploader. Production guards then rejected drift before
and after rendering for either input. A test's incorrect decision-enum member was also corrected.
Neither test-harness correction required a production behavior change.

Fresh branch review found two important issues. A valid saved record could be replaced
without taking the cooperating-writer lock while a renderer ran; four regressions failed
before the fix (comparison callback, shared JSON/HTML exports and identifier formatting).
The shared deferred review export now rereads and fingerprints the saved record after
rendering. Test and supplying-run identifiers use literal code cells so Markdown cannot
collapse distinct identifiers. All four regressions then passed; the installed-browser
case checks the actual displayed distinction between `suite/_smoke_` and `suite/smoke`.

One minor remains deferred: the inline run table shows changed records without raw
outcomes; the complete HTML report includes both outcome assertions. No evidence or
acceptance rule depends on that preview omission.

The installed-browser regression exercises explicit selection, source citations, an actual
HTML download, offline desktop/phone reading, invalid prior input and byte-identical saved
records. Local browser/package execution is unavailable under the current environment policy;
exact-head hosted CI supplies those results. PR records carry final full-suite, coverage,
Windows, installed-package, browser and resulting-main outcomes; focused checks alone are
not substituted for those results.

## Integration and remaining stages

#305 merged with its reviewed head pinned. #306 was retargeted to main; main's required
CodeQL check was absent on the former stacked branch. Merging the new main parent into
that branch preserved the exact tested source tree and triggered protected checks. No branch
protection was changed or bypassed. The workbench follow-on is reviewed separately.

Release packaging/publication and Pages deployment remain separate decisions. Independent
usefulness, repeat use and demand remain unmeasured; constructed automation creates no
independent-use evidence. Broader private access, sharing or integrations remain gated by
demonstrated needs. No participant contact or personal testing is initiated.

After the review fixes, 294 focused checks passed with two intentional browser skips.
Whole-repository Ruff, whitespace and frozen-path checks passed before sync.

The first hosted run passed its source, coverage, installed CLI, Python and Windows checks,
and 38 browser cases. The new browser journey stopped at `Locator.check`: Streamlit's visible
label intercepted the hidden input's pointer target. The journey now activates that visible
label, as existing workbench tests do, and asserts the actual checked state before continuing.
The corrected exact-head run must verify the remaining installed comparison journey.
