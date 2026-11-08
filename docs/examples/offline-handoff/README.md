# Inspect a constructed handoff without installing ScopeProof

[Download the sample ZIP](https://github.com/YuzeJ21/Scope-Proof/raw/refs/heads/main/docs/examples/offline-handoff/constructed-v026-review.zip),
extract it, and open `constructed-v026-review.html` in a browser. The report is self-contained
and can be read offline. The archive contains only that labelled HTML file. GitHub serves raw
HTML as text; the ZIP provides a normal binary download without requiring ScopeProof installation.

Expected current result: **Action required**, final acceptance **No**, criteria revision **2**,
blocker **AC-03**. Read the reasons, next action and recorded decision audit. This is an active
full-state report with audit context, not an importable saved record or an export of every retained
analysis. Earlier acceptance remains prior-revision history and does not control the current gate.

**Every actor, decision, CI observation and runtime statement is constructed automation.** No
target code or tests were executed and no person used or approved the product. The repository/head
and source links are synthetic; they do not resolve to genuine reviewed source. Opening or
downloading the example supplies no qualifying-review, independent-use or customer-validation credit.

## Identity and presentation

The actual installed **public v0.2.6** package produced the report. Its source is
`68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1`; its verified public wheel SHA-256 is
`48b308b3f92d912932734aa4907e958d78351bb956f1a9ce65353e9206741896`.
This does not relabel current `0.2.7.dev0` development as a released producer.

The input is the existing immutable
[`active-rich-v9.json`](../../../tests/fixtures/released_v026_upgrade/active-rich-v9.json),
SHA-256 `044793a5894c13da7bd846f6926bbeac39955389c8897cdecaaf0bbe4e7b0ba5`.
It is read through the released package's Pydantic storage boundary and is never resaved or revised.
Its original [corpus provenance](../../../tests/fixtures/released_v026_upgrade/provenance.json)
and historical results remain unchanged.

The public exporter produced 37,078 bytes, SHA-256
`99b1e798b58f929969b8a72b4862220c9b473eef37a86d89f8f72ec1f6b49275`.
The only presentation change is one upfront constructed-example disclosure immediately after
`<body>`. Removing that exact disclosure recovers the original exporter bytes. The verdict,
evidence, decisions and audit text are not edited. The [strict manifest](provenance.json) separately
binds the input, recipe, original export and presented report. It is provenance, not an import file.
It also binds the deterministic ZIP wrapper, whose only entry is the presented HTML; fixed ZIP
metadata permits repeatable bytes in the verified generation environment.

## Regenerate without replacing historical evidence

Use an isolated environment with the verified public v0.2.6 wheel installed, outside the checkout.
Check its [Release entry](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6) for the public
wheel and checksum verification. From outside the repository, run its installed Python:

```bash
/absolute/public-v026-env/bin/python -I /absolute/ScopeProof/scripts/build_offline_handoff_sample.py \
  --record /absolute/ScopeProof/tests/fixtures/released_v026_upgrade/active-rich-v9.json \
  --wheel /absolute/downloads/scopeproof-0.2.6-py3-none-any.whl \
  --output-dir /absolute/new-sample-directory
```

On Windows, use that environment's `Scripts/python.exe`. Existing output directories are refused.
The recipe requires the actual installed public core and wheel identities, preserves input bytes,
and rejects network/process execution during export. Generate into two new directories and compare
the HTML, ZIP and manifest bytes; timestamps and decisions belong to the unchanged constructed input.
Do not regenerate the native corpus or edit the sample to improve a gate result.

Automated checks cover provenance rejection, exact raw/presented bytes and disclosure, expected
blocked semantics, no executable/remote dependencies, offline desktop/mobile rendering and no
automatic network requests. These are engineering checks, not accessibility conformance or genuine
use. The current website remains the separately verified `388b7da` publication; its evaluation-guide
link reaches this repository download. No new package or Pages publication is part of this slice.
