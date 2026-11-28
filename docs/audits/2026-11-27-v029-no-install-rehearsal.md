# v0.2.9 no-install walkthrough rehearsal

On November 27, 2026, an engineering rehearsal started at the signed-out
[public evaluation guide](../evaluation-guide.md). It used only the existing
constructed example and a browser to view the extracted HTML. No ScopeProof
installation, application server or target code execution was needed.

## Download

The guide's ZIP link opened a GitHub error page and did not download a file.
The [walkthrough guide](../examples/ci-handoff/README.md) pointed to the same
`blob/main/…zip?raw=true` destination. The ZIP preview's **View raw** link
downloaded successfully in the same signed-out session. Both guides now use
that direct download URL. The downloaded 19,899-byte ZIP matched the checked-in
archive byte for byte; its SHA-256 is
`827679498935d839be05ac14dd3382b186daefa9b4936853122cc33a31ba8582`.

## Reviewer result

- **What changed:** The initial and targeted snapshots review the same Build B
  commit, `aac2fb06cb315a392e91e432f3d862607c7e9856`. Only AC-02 row access
  (`row_entitlement`) changes from explicitly skipped to failed. AC-01
  category filtering remains failed and AC-03 CSV header remains passed; both
  results cite initial run `B`. The new failure cites `B-targeted`.
- **Acceptance:** The index shows **Action required** and recorded final
  acceptance **No** for all three moments, including Build A with three
  passing checks. Both Build B cards link to the same saved review. The
  snapshots label CI as externally supplied and say they do not record an
  acceptance decision.
- **What to check next:** Open the supplied manifests to trace the AC-01
  filter failure to the initial B run and the AC-02 row-access failure to the
  targeted run. Review both against the same Build B commit before revisiting
  acceptance. The added CI result does not resolve either criterion.

The extracted walkthrough supplied the information needed for all three
questions without a new example or product change. Pause feature work.
This rehearsal provides engineering evidence about the evaluation path; it
does not establish independent reviewer usability, genuine CI execution,
customer use, or acceptance. No release, Pages deployment, or outreach was
part of the rehearsal.
