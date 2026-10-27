# Packaged browser investigation — 2026-10-27

The intermittent missing-dropdown failure remains **unproven and unfixed**. This
change adds failure evidence so a recurrence can be investigated without guessing
from a final accessibility snapshot. It changes no application, gate, selection,
or retry behavior.

## Observed evidence

| Run | Head | Packaged browser result |
| --- | --- | --- |
| [PR #208 attempt 1](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40436001259/attempts/1) | `fffcbd302743975a25d6de2f5522b7eaef38d686` | 1 failed, 4 passed in 27.30s |
| [Same-head attempt 2](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40436001259/attempts/2) | `fffcbd302743975a25d6de2f5522b7eaef38d686` | 5 passed in 42.63s |
| [Resulting main](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40439000294) | `c883ff871b414e223a85d7a50a7ad5a361a506b4` | 5 passed in 46.94s |

The failed attempt reached `_exercise_junit_import_round_trip` and called
`_choose_combobox_option` for `File scope decision`. Its assertion waited five
seconds for the `Outside Confirmed Criteria` option, then raised `AssertionError`
because no matching option existed. The helper retries `PlaywrightTimeoutError`,
so this assertion did not enter its retry handler.

The final snapshot contained the requested combobox text and no open option.
However, the helper had just called `combobox.fill(option_name)` before waiting
for the option. That input text alone cannot distinguish a search query from a
committed Streamlit selection. Returning success solely from the text would not
establish that the server received the selection. The snapshot does not show why
the dropdown disappeared, when it closed, or which rerun was active.

The application renders this control with `st.selectbox`, `index=None`, a display
formatter, and the `scope_disposition` session key. No application defect or
Streamlit defect was established by reading that rendering code.

## Bounded local reproduction

An unchanged packaged journey was run in isolated temporary storage with loopback
request restrictions:

```text
uv run --no-sync python -m pytest -q -m browser \
  tests/browser/test_packaged_workbench.py::test_installed_wheel_primary_path_in_chromium \
  --basetemp /tmp/scopeproof-browser-investigation-observed
1 passed in 38.28s
```

This did not reproduce the failure. A passing journey does not explain or resolve
the intermittent failure. No controlled reproduction of the original dropdown
race was obtained, so selection fallbacks and broader retries were not added.

## Diagnostic change and verification

Each constructed installed-wheel viewport journey records a Playwright trace.
On failure it saves `trace.zip`, `failure.png`, `failure.aria.txt`, and a copy of
the workbench `server.log` before closing the browser. Successful journeys discard
the trace without writing these diagnostics. The default destination is the test's
temporary directory; CI sets `SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR` to a runner-temporary
directory and uploads available diagnostics only after failure, for seven days.
These artifacts contain the existing disposable, deliberately constructed review
fixtures, not participant evidence.

Each capture is attempted independently. Capture errors are added as notes to the
original journey exception, which is re-raised unchanged. A missing server log
must therefore leave the screenshot, accessibility snapshot, and trace available
without replacing the real failure.

Two real Chromium controlled-failure cases cover complete capture and missing-log
capture. They check the original exception identity, PNG signature, accessibility
content, readable trace archive, and copied log or capture-error note. The tests
were first observed failing because the capture helper was absent, then passed
after its implementation. Focused verification:

```text
uv run --no-sync python -m pytest -q -m browser \
  tests/browser/test_packaged_workbench.py -k 'not installed_wheel'
6 passed, 1 deselected in 1.03s

uv run --no-sync python -m ruff check tests/browser/test_packaged_workbench.py
All checks passed!

git diff --check
exit 0
```

The controlled failure verifies diagnostic capture, not reproduction or repair of
the missing dropdown. The installed-wheel baseline preceded this diagnostic
change; it is not evidence that the final changed journey has passed. The root
task owns repository-wide and final packaged-journey verification. Hosted upload
delivery has not been exercised by a failing CI run with this change.

On recurrence, inspect the trace actions and DOM snapshots around the file-path
selection, the disposition click/fill, and the missing option assertion alongside
the server log. Establish the input, focus, dropdown, and rerun sequence before
changing the helper or application.
