# Follow a CI handoff without installing

[Download the walkthrough ZIP](https://github.com/YuzeJ21/Scope-Proof/raw/refs/heads/main/docs/examples/ci-handoff/reader/constructed-ci-walkthrough.zip),
extract it to one directory, and open `index.html`. The HTML pages and local JSON links
work offline. Following an illustrative external run link requires a connection and
does not reach a genuine CI run.

The walkthrough shows three moments at two exact constructed commits:

| Moment | Category filter / AC-01 | Row access / AC-02 | CSV header / AC-03 |
| --- | --- | --- | --- |
| A · baseline | Passed | Passed | Passed |
| B · initial | Failed | Explicitly skipped | Passed |
| B · after targeted rerun | Failed | Failed | Passed |

The table shows effective CI status at each moment. The targeted rerun executes only
row access. The filter failure and header pass retain their initial B run citations;
the walkthrough identifies the supplying run beside every result.

Build A is `2a95b61bcbbf2f3a07bc0ee8bde09dd4c58cb942`.
Both Build B snapshots use `aac2fb06cb315a392e91e432f3d862607c7e9856`.
The targeted run adds a failure result; it does not fix the implementation.

At every moment the saved acceptance review remains **Action required**, with final
acceptance **No**. Even A's passing checks establish no reviewer decision, required
external verification or scope closure. Each card explains what to check next and
links its supplied manifest and unchanged saved review. All inputs, actors, tickets,
commits and run links belong to the constructed fixture. No target PR code is executed.

## Original producer and presentation

The existing private **0.2.9.dev0** candidate produced these snapshots from source
`f8be51021bb95c596802426ef05c15fabf393975`, tree
`08b3456367a5f50ed5c31c492d642d5c80d80ca8`. Its wheel SHA-256 is
`62eb1fdcb25c2b63d74acd26cdba06c8556537c0cda5d78022cfc1a3a86ad1ef`.
The recorded wheel's 108 core/UI Python files were compared with that exact Git
source during this integration. The candidate and its package bytes were not rebuilt.
The public evaluation package remains [v0.2.8](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.8).

`source/` retains the exact original reports as `.html.txt`, original producer record,
CI manifests, raw synthetic check results and two saved reviews. All JSON inputs pass
their applicable Pydantic schemas before presentation. A pinned original-provenance
digest binds the archived reports and inputs. This is byte identity, not a signature
or authenticated execution attestation.

The presentation adds exactly one upfront constructed-example disclosure to each
original snapshot. Removing the exact `DISCLOSURE` string from the recipe recovers
the original snapshot bytes. The new index explains the next action and recorded
acceptance status. `reader/provenance.json` binds the original producer, presentation
recipe, original snapshot hashes and output artifacts. `reader/download.json` binds
the ZIP and provenance file. The ZIP includes the index, three snapshots, original
provenance and all eight constructed JSON inputs; it includes no executable code.

## Reproduce the presentation

From a development checkout with its existing dependencies installed, choose a new
output directory:

```sh
python -m scripts.build_ci_walkthrough docs/examples/ci-handoff/source /tmp/scopeproof-ci-reader
```

The recipe validates the frozen inputs, rejects changed reports and existing outputs,
and writes a deterministic presentation and ZIP. It runs no simulator, tests, target
code or network requests. Original saved reviews and manifests remain byte-identical.
Freshly generating the same inputs twice produces identical output files.

Run the source and offline-browser contracts with:

```sh
python -m pytest -q tests/test_ci_walkthrough.py
python -m pytest -q -m browser tests/test_ci_walkthrough.py
```

The browser check requires the existing Playwright Chromium installation. It reads
all four pages offline at desktop and phone widths, checks local links and horizontal
containment, exercises narrow snapshot tables by keyboard, and checks for zero
automatic external requests. These checks do not establish accessibility conformance,
customer value or independent repeat use. The original v0.2.6 sample and frozen R-002
research remain unchanged. No package release or Pages deployment accompanies this example.
