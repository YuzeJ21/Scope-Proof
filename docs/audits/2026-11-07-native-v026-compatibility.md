# Native public-v0.2.6 saved-history compatibility — 2026-11-07

Baseline: published v0.2.6 and main `68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1`.
Development source advances to unpublished `0.2.7.dev0`; the public release remains unchanged.

## Gap and bounded outcome

The repository already preserves one native public-v0.2.3/v0.2.4 upgrade fixture. Rich v9
histories were exercised during private release verification, but had no committed native
released-writer baseline. Tests that construct a record with the current writer and read it
with the current reader can miss drift shared by both. No current data-loss defect was reproduced.

The new [corpus](../../tests/fixtures/released_v026_upgrade/provenance.json) retains two native-v9
records created through supported APIs by the actual installed public v0.2.6 package:

| Constructed record | Current lifecycle | Retained analyses |
| --- | --- | --- |
| `active-rich-v9.json` | Confirmed revision 2, active Blocked | Revision 1 Ready |
| `pending-rich-v9.json` | Unconfirmed revision 3, no active analysis | Revision 1 Ready, revision 2 Blocked |

Both contain nine resolution events, two constructed runtime assertions, four selected references
and four correction/withdrawal events, two JUnit imports with four correction/withdrawal events,
and two explicit file-scope decisions. The synthetic earlier Ready/acceptance is retained history,
not current acceptance. Every actor and assertion is labelled constructed; none earns actual
target-runtime, human-use or qualifying-review credit.

## Native writer and byte provenance

The standalone [recipe](../../tests/fixtures/released_v026_upgrade/generate_records.py) requires
isolated Python in the verified public installation, outside the checkout, and refuses existing
output. It validates the actual package/core version, native record version, public wheel and
checksum hashes, installed core fingerprint and packaged fixture inputs. It does not relabel
records from another writer. An audit hook blocks network connections and external process
execution during construction. CI reads committed bytes; it does not regenerate them.

The [strict Pydantic manifest schema](../../tests/fixtures/released_v026_upgrade/provenance_schema.py)
binds producer identity, lifecycle, counts and artifact digests and rejects altered credit flags
and coercions. The manifest also hashes the generation recipe and schema. Record timestamps are
construction timestamps, not evidence of human actions. Original bytes are preserved with Git
text conversion disabled, including on Windows.

- Public writer wheel SHA-256: `48b308b3f92d912932734aa4907e958d78351bb956f1a9ce65353e9206741896`.
- Producer core SHA-256: `7b3a9180fa8658e800486cac4cc0cb1a3ff236bb88c0ad9c9f165a699e04eb64`.
- Active record SHA-256: `044793a5894c13da7bd846f6926bbeac39955389c8897cdecaaf0bbe4e7b0ba5`.
- Pending record SHA-256: `bde341db1b28b4f2b5531748f63913dae32291c2eac63c46ec4acdec4e20a0b9`.

## Regression contract

[Permanent tests](../../tests/storage/test_released_v026_upgrade.py) compare the complete native
state, not an allowlist of surviving fields. Repeated load may not modify the original. Only
temporary copies are resaved; their complete state and recorded v0.2.6 producer remain intact.
Explicit assertions check revision/confirmation, gates, runtime links, resolution status,
reference replacement/withdrawal, original and corrected JUnit mappings, import withdrawal,
scope decisions and source provenance.

Inspection, download, file export and both import APIs preserve raw bytes. Recipient reopening
must preserve complete state and producer identity. Duplicate imports/exports cannot overwrite
existing files. Active JSON preserves full lifecycle state; readable reports retain the current
analysis and its audit facts. Pending current-state reports continue to reject unconfirmed state.
Explicitly selecting a retained bundle can produce an analysis-only report; that report does
not represent the pending review's complete lifecycle or establish current acceptance.

The tests run with the existing Linux full suites and the Windows released-record lane. Existing
installed CLI/browser journeys, locked-environment contracts, lint, deterministic benchmarks and
the unrounded 95% coverage floor remain required. Exact-head CI and independent engineering
review are merge gates; resulting-main checks are verified separately. Final execution counts
and review dispositions are recorded with the PR and external verification logs.

## Separate remaining gap and limits

During construction, an explicit retained revision-2 bundle exposed an existing report-label
limitation: CSV and HTML derive their lifecycle revision display from a default revision when
no complete `ReviewState` is supplied. They can show revision 1 although the bundle's
`criteria_revision_number` is 2; Markdown omits that lifecycle revision. JSON retains the bundle's
correct revision. This change does not alter exporters or assert those labels as desired behavior.
A subsequent bounded fix should preserve analysis-only semantics and pending current-report
denial while deriving displayed analysis revision from the selected bundle. It must not fabricate
a current state to obtain a report.

This corpus covers two constructed records, not every record, platform or dependency combination.
It adds no actor authentication, historical executable replay, downgrade guarantee, target-code
execution or hostile-markup probe. Existing hostile-rendering regressions remain separate.
Frozen R-002 inputs/results and older native fixtures remain unchanged. The already-closed
R-002 miss taxonomy is not repeated or retuned.

Stage 2 remains owner-led productization. Stage 3 is dormant pending genuine independent-use
evidence and separate authorization. No personal testing, qualifying reviews, new release,
deployment or outreach is performed or implied.
