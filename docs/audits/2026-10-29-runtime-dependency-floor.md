# Dependency-floor and JUnit upload assessment — 2026-10-29

## Question and identities

Does the published package work at its declared direct dependency minimums, and is that combination
consistent with current dependency guidance? The owner delegated automatic investigation and
declined personal testing and qualifying reviews. At start, PR #218 was merged; main
`588dcb979c9f4900c32bfb959f70c8babc1921c0` and its CI were green. No engineering defect report or
open engineering PR supplied a separate feature requirement. This is one bounded compatibility
assessment, followed by one demonstrated application repair.

Fresh anonymous downloads returned HTTP 200 and matched the unchanged public manifest:

| Artifact | Identity |
| --- | --- |
| Public v0.2.4 source / peeled tag | `11bcdc66f7d8f5a29055688208de1ed337eed07f` |
| `scopeproof-0.2.4-py3-none-any.whl` | SHA-256 `350ec7375ddab278f4dfef9737c341b5f26fe6e23dff7d0568df363cd4f3a287` |
| `SHA256SUMS.txt` | SHA-256 `ab2de99af4bfbbd595794f7cb7d11254f2acdd27c3ca258bf1a6e0a0cc53d7c7` |
| Repaired source candidate | `b575447a3dee08244b9e004f8fe4a3a36a492e8d`, unreleased `0.2.5.dev0` |
| Candidate wheel | SHA-256 `b6a2f964125cdcc6e61a9661bfcbed05f62be31255aaa3960280b415cc7c8619` |

Each environment was created outside the checkout with genuine Python **3.11.15**. Each used one
resolver transaction containing the wheel and all exact requested versions; `pip check` passed.
Isolated-mode import guards required the package to reside under that environment's prefix.
Pydantic-validated private records retain full resolved dependency maps, import paths, commands,
logs, original failures and browser traces. They are not public telemetry or participant records.

## Observed combinations

| Installed package | HTTPX / Pydantic | Streamlit / Pillow | Observed result |
| --- | --- | --- | --- |
| Public v0.2.4, declared floors | 0.27.0 / 2.8.0 | 1.53.0 / 12.3.0 | CLI/core checks passed; browser primary path reached deferred exports, then the current saved-review selector helper failed. Full UI compatibility remains unverified. |
| Same public v0.2.4 wheel, maintained UI | 0.27.0 / 2.8.0 | 1.66.1 / 13.0.0 | Full existing primary and JUnit roundtrip passed; valid exact-1-MiB XML was rejected by the upload frontend. |
| Repaired source candidate | 0.27.0 / 2.8.0 | 1.66.1 / 13.0.0 | Full existing primary and JUnit roundtrip, exact-1-MiB inspection, and one-byte-over rejection passed. Broader source tests subsequently found R-002 validation incompatibility; this is not a full compatibility pass. |

The first combination passed installed CLI and workbench version checks, all **12 constructed
acceptance benchmark cases** and **2 comparison cases**, with no expected-result mismatch.
One constructed demo review saved and reopened; JSON, Markdown, HTML and CSV exports succeeded,
with JSON revalidated against its schema. Its gate stayed Blocked and final acceptance stayed false.
None of these operations ran target-repository code.

On Streamlit 1.53.0, a separate diagnostic showed that clicking the saved-review option actually
selected it and enabled Reopen. Its accessible name then changed to include the selected value,
which the current exact-name helper did not expect. This establishes a helper/DOM mismatch, not a
demonstrated product reopening defect. The original failure is retained and the old-stack journey
is explicitly partial; no helper workaround was used to manufacture a full compatibility pass.

A separate **current-source** full suite under Python 3.11.15, HTTPX 0.27.0, Pydantic 2.8.0,
Streamlit 1.66.1 and Pillow 13.0.0 returned **2,653 passed, 55 failed, 9 skipped** at `cd1d69d`.
The failed tests concern R-002 strict JSON validation and its packaged-input contract. A narrow
independent diagnostic confirmed an actual product incompatibility: a fully typed constructed
20-case `R002CriteriaSet` serializes to canonical JSON, then rejects its own criterion enum strings
under Pydantic 2.8.0. Persisted criteria loading and annotation validation use this same path.
The affected models, runner and core schemas are byte-identical in the public release, starting
main and candidate; the upload change did not introduce it. The same canonical input passes with
the locked Pydantic 2.13.4 under the same Python 3.11.15 interpreter. Both diagnostic inputs are
7,453 bytes with SHA-256 `a74fb3bdf1c3c4f8571ac9cc47cf07db1ad52627a178ea56c55e7c17e0340bf4`.
The original failed log is retained; it is not replaced by a passing
run with different dependencies. No frozen R-002 input, label, expectation or result was rewritten.

## Dependency-policy limit

Streamlit 1.53.0 declares `pillow>=7.1.0,<13`; the fresh resolution selected Pillow 12.3.0.
The checked-in development baseline uses Pillow 13.0.0, the first patched version for the documented
current advisories. Requesting the exact old Streamlit floor together with `Pillow>=13,<14` failed
resolution as expected. See the maintainer's [13.0.0 release notes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html)
and [representative advisory](https://github.com/python-pillow/Pillow/security/advisories/GHSA-332p-7hrc-92wf).
This is a dependency-policy conflict, not evidence that ScopeProof was exploited or that the
constructed workflows reached an affected image operation.

Current installation guidance therefore explicitly requests `pydantic>=2.13.4,<3`,
`streamlit>=1.66.1,<2` and `Pillow>=13,<14` alongside the immutable public wheel. Pydantic 2.13.4
is the locked baseline, not a newly established earliest working version. The exact browser
combinations observed above still used Pydantic 2.8.0 and retain that narrower scope. A separate
Python 3.11 source-suite check uses the maintained Pydantic baseline; its exact-head result is in
the PR verification record. The earlier observed combinations remain in the
table above. These ranges are guidance, not a claim that every allowed future resolution has been
verified or is free of advisories. The existing lock remains the reproducible contributor baseline.
The historical Streamlit lower bound identifies an API minimum; it is not a blanket maintained
support promise. No package metadata, dependency lock or standing CI matrix was changed here.
The additional Pydantic incompatibility is documented rather than expanding this one-repair goal
into a second code change or weakening strict validation. Declared minimums remain more permissive
than the fully verified environment; any later metadata correction needs its own bounded evidence.

## Reproduced defect and one repair

The application and parser use a binary **1 MiB = 1,048,576 bytes** cap. Before this repair the
upload widget used `max_upload_size=1`. The installed Streamlit frontend uses decimal MB on
non-Windows browser platforms and binary units on Windows. On the observed macOS Chromium
platform, it rejected valid 1,048,576-byte XML with “File must be 1.0MB or smaller.” The artifact
never reached ScopeProof's size guard. Public v0.2.4 and starting main had identical app source,
and the error reproduced on the maintained dependency combination, so this was not merely an
old-dependency problem.

The unreleased repair changes only the JUnit widget allowance to **2 MB** and explains the exact
payload cap beside it. The existing early `uploaded_junit.size > MAX_JUNIT_BYTES` check still
rejects oversized artifacts **before `getvalue()` or parsing**. The parser cap, global transport
configuration, evidence schema, mappings, reviewer decisions, criteria confirmation, deterministic
gates and core/UI boundary are unchanged. A larger transport allowance does not authorize a larger
import. No target code executes.

The exact-boundary AppTest first failed against the old widget allowance. With the repair it
inspects and saves valid exact-cap XML, checks the artifact digest and requires unchanged gate,
resolutions, runtime evidence and final acceptance. A separate one-byte-over case patches
`UploadedFile.getvalue()` to raise and requires that it is never called, while preview is absent,
saving is disabled and prior review state survives. The focused AppTest/importer run passed
**51 tests**.

The candidate wheel's **64 packaged Python files** matched source commit `b575447` byte for byte.
Its complete resolved runtime dependency versions matched the maintained public-wheel environment
except for ScopeProof's own version. The independent browser controller used current checkout
helpers and Playwright 1.62.0 under Python 3.12.0; the loopback server and constructed fixture
generation used the guarded installed Python 3.11 candidate environment. This separation is
recorded rather than implying that checkout helper code was part of the installed server.

The first candidate run reached a valid sanitized preview but failed because its expander collapsed
on upload rerun. Helper-only commit `74ebacef5ec5fa868473af06e02b640eb5f5b7c9` reopens the panel when
needed and retains the visibility assertions. The original trace remains. The complete rerun passed:

- Keyboard primary workflow, autosave/reopen and deferred Markdown/CSV downloads.
- Constructed JUnit mapping, persistence/reopen and sanitized Markdown/JSON downloads.
- Exact-cap XML preview and computed result counts.
- 1,048,577-byte rejection, absent preview, disabled Save and the previous import preserved.

No external browser requests or page errors were observed; the loopback server process group was
stopped. This was one constructed desktop viewport, not Windows desktop or accessibility evidence.

## Integration and stopping boundary

Full-suite coverage, lint, deterministic benchmarks, packaged-browser checks, Python/Windows CI
and independent automated review must pass for the exact PR head before guarded merge. Their
commands, outcomes and resulting-main identity belong in the PR verification record. Dated results
above remain bound to their actual wheels and source commits; new CI counts do not rewrite them.

The published v0.2.4 package **retains the upload defect**. Its CLI `inspect-junit` / `import-junit`
path accepts the exact binary cap and is the documented full-size workaround. This assessment
does not publish a replacement package or change release assets/tags. Source remains unreleased
`0.2.5.dev0`; a further release needs separate authorization.

After reviewed passing integration, stop and return to bounded maintenance. Frozen R-002 inputs
and results remain unchanged. All actors and cases here are constructed automation, with **zero
genuine independent-use credit**. Stage 1 remains closed at zero and Stage 3 dormant and gated.
No personal testing, qualifying reviews, customer validation, beta completion, accessibility
conformance, deployment or outreach is claimed or initiated.
