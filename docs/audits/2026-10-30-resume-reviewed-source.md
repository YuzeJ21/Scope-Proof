# Saved-source continuation and bounded gap review — 2026-10-30

Baseline main: `2b94db2bd02661d99e0cfdd2f4fdd63dd914a2ef` (PR #229). Fresh GitHub reads verified
its CI, CodeQL push and base-advance workflows passed; both checkouts were clean/synchronized
and there were no open PRs. This assessment concerns unreleased 0.2.5 source, not public v0.2.4
or private candidate archives at `4f12ae02dee277705d17ac6ab94f0a74f99be346`.

## Inspected gaps and selection

| Demonstrated limitation | Effect on the existing workflow | Disposition |
| --- | --- | --- |
| Reopen clears source; Check current head resets the analysis even when the snapshot matches. | Continuing selected-reference work requires replacing confirmation/analysis. Original saved bytes survive, so this is blocked continuation rather than data loss. | Selected: explicit matching-source attachment without replacing the analysis. |
| Selected references cannot be corrected or withdrawn; duplicate location blocks a corrected append. | Incorrect mapping/rationale stays in the active collection. | Larger independent audit-history/schema design; not included or added to a standing queue. |
| Reopen discovery exposes opaque IDs without record metadata. | Finding a known saved review requires its ID. | Lower-impact discovery limitation; not included in this outcome. |

An independent constructed AppTest reproduction saved a reference, restarted, reopened, and supplied
the identical source to Check current head. The session became unconfirmed with no active bundle;
the original saved JSON and reference remained intact. This concrete implementation gap supports
an engineering improvement, not a claim of practitioner demand or product-market fit.

## Supported treatment

**Load matching reviewed source** is a separate action. A pure core Pydantic receipt binds the
source context and exact source bytes. Full saved/current fingerprints are checked under the
storage lock after network work finishes. No network occurs under that lock and attachment
writes no review bytes. The ongoing context deliberately excludes final acceptance while retaining
review identity/source facts, criteria revision/provenance and producer metadata, so legitimate
reference/decision appends do not expire unchanged source after the first save.

Attachment requires complete confirmed active state, known exact inventory, matching repository,
PR, base/head, visibility, ingestion and full CI observation, with no skipped/warning/truncated
source. Recorded selected references must remain exact eligible raw lines. Unchanged files come
only from the union of recorded automatic/selected paths, at most eight files and 200,000 UTF-8
bytes in total; responses must cover those paths once at the reviewed head without aliases.
Unrecorded inputs are not reconstructed. Verified-public live loading uses the existing bounded
client; explicit demo loading remains offline/constructed. Other origins fail closed.

Fresh contradictory source facts block current workbench authority, final acceptance and exports,
including queued deferred callbacks. The original saved gate remains inspectable as historical.
The dedicated session guard survives draft clearing/reopening of the same context, and is distinct
from persisted-state conflicts. Explicit matching-source recovery or a new analysis is required.
This volatile guard is not a global revocation of historical records or downloaded reports and
does not monitor CI continuously. Check current head retains its explicit re-review behavior.

## Verification and remaining evidence boundary

New core and AppTest cases were observed RED before implementation. Coverage includes preserved
state/bytes, source/CI/origin mismatches, candidate bounds, stale fetch transactions, source-neutral
appends, source tampering, conflict persistence and old export callbacks. Additional independently
authored concurrency coverage exposed a widget-reset failure after stale attachment rejection;
the failed path now reconciles at the top of a fresh render before comparison widgets exist.

The constructed installed-wheel journey reopens, loads matching source explicitly, saves a second
reference and validates unchanged first-reference/analysis/decision facts plus JSON/Markdown/CSV
and persisted-store results. Simulated live actors and demo actors are labeled constructed;
neither supplies genuine independent-use evidence. Exact local/head/main commands, results,
independent review and frozen-byte manifests are retained in the integration record and private
audit folder `/Users/yjian070/Documents/ScopeProof-product-audits/2026-10-30-resume-reviewed-source`.

Record v6, deterministic gates, runtime distinctions, 32-reference/4,096-byte line limits,
frozen R-002 inputs/results, public release and private candidate bytes remain unchanged.
Usefulness, independent repeat use and demand remain unknown. The owner declines personal testing
and qualifying reviews; Stage 3 remains dormant pending genuine independent use and separate
authorization. No release, deployment, outreach or public marketing is included.
