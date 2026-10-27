# Browser maintenance investigation

## Intent and evidence

Investigate the intermittent packaged-browser failure automatically, without personal testing or
qualifying reviews. The baseline is main `9301e77b1eec1aa0e14bfdc45fa6a2fd3c8cf70e`.
The original missing-dropdown failure is not yet reproduced or explained.

Three unchanged installed-wheel journeys passed; the fourth failed after a Markdown download,
with the deferred JSON download stuck loading. Its trace and server log were preserved. A separate
real Streamlit experiment reproduced a false-success defect in `_choose_combobox_option`:
matching query text made the helper return while the server selection remained `None`.

## Approach

Use real Chromium and Streamlit to test committed selection independently of input text. Keep
the helper's existing bounded retry count, and never convert a missing option or uncommitted query
into success. Already committed selections must not wait for a rerun that will not occur.

For downloads, establish a failing regression before changing application behavior. Investigate
the default download-triggered rerun together with callable data generation. If suppressing that
unnecessary rerun is supported by the reproduction, preserve the existing click-time locked-load,
fingerprint comparison, validation, pending-input guard, and export bytes. Otherwise leave the
download finding explicitly unresolved.

Increasing timeouts or retrying the whole journey would hide the distinction between a transient
interaction and a stuck operation. Changing gates, criteria confirmation, reviewer decisions,
framework internals, or frozen benchmark labels is outside this repair.

## Completion

Observe each new regression fail against unchanged code, then pass with the minimal repair. Run
the full suite with unrounded coverage at least 95%, lint, deterministic benchmarks, and the
installed-wheel browser file. Obtain independent agent review and resolve supported findings.
Merge only after exact-head CI passes, then verify resulting main. Keep original, newly observed,
and controlled failures distinct; browser automation creates no independent-use evidence.

There is no release, deployment, outreach, Stage 3 transition, or recurring monitor.
