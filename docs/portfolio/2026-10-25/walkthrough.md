# Automated constructed walkthrough

Core integrity revision: unreleased `0.2.4.dev0` draft at
`47ebc4f275b9f307c9305af3890782fa7578dff4`. The fixture actor called
“Packaged browser reviewer” is automation, not a real confirmer or participant.

The installed-wheel Chromium journey is
`tests/browser/test_packaged_workbench.py::test_installed_wheel_primary_path_in_chromium`.
It runs the app with review, alpha, and rehearsal storage under a temporary runtime home and
blocks non-loopback browser traffic. To recreate the screenshots from the source checkout:

```bash
SCOPEPROOF_PORTFOLIO_CAPTURE_DIR=docs/portfolio/2026-10-25/assets \
  python -B -m pytest -p no:cacheprovider -q -m browser \
  tests/browser/test_packaged_workbench.py
```

| Step | Automated observation | Local capture |
| --- | --- | --- |
| Load deliberately constructed demo | The app displays editable normalized criteria and asks for a confirmer. | [Criteria before confirmation](assets/01-confirm-criteria.png) |
| Confirm exact criteria | Automation types a fixture actor and activates the explicit confirmation control. This simulates a UI interaction; it is not genuine requirements authority. | [Confirmation state](assets/02-criteria-confirmed.png) |
| Run deterministic analysis | The constructed review shows decision progress and an unresolved criteria queue. | [Decision progress](assets/03-decision-progress.png) |
| Inspect partial support | A criterion shows five accepted candidates and explains that stronger evidence is still missing; a candidate is not proof of satisfaction. | [Partial support](assets/04-partial-support.png) |
| Inspect exports | The constructed review exposes Markdown, JSON, and CSV download controls after analysis. | [Export controls](assets/05-export-controls.png) |
| Inspect criterion review | The capture shows the AC-02 review card and its decision-control trigger. The test then opens that control and checks that the human-decision selector is present before the secondary evidence matrix. It does not assert a human decision. | [Criterion review card](assets/06-criterion-review-card.png) |
| Export and reopen | The automation downloads Markdown, checks the constructed head SHA in the bytes, and reopens the validated local review. | Covered by the test assertions; no separate screenshot. |

The changed-head case is a separate deterministic mocked-GitHub regression:
`tests/github/test_client.py::test_fetch_rejects_aba_revision_with_foreign_mutable_patch`
and `tests/github/test_pagination_and_candidates.py::test_aba_movement_between_file_pages_is_rejected_by_immutable_comparison`.
The mock starts and ends at head A while a mutable file page belongs to B. ScopeProof compares
the page against GitHub's SHA-addressed A snapshot and raises `GitHubIngestionError` before a
review bundle or Ready decision can be produced. The diagram and case study show this boundary;
it is an automated synthetic trace, not a live GitHub incident.

These checks demonstrate engineering behavior in the available local environment. They do not
establish customer usefulness, accessibility conformance, or correct runtime behavior of a
third-party pull request.
