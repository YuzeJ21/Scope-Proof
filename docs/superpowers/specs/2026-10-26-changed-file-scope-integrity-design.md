# Changed-file scope integrity design

ScopeProof currently returns Ready for the constructed `scope-expansion` case even though `src/auth.py` changed and no criterion cites it. The snapshot contains that file; review construction drops the file list before gate evaluation. A passing criterion and final acceptance therefore mask an unexamined change.

The review will retain a Pydantic-validated inventory of inspectable changed paths and statuses, bound to its exact head SHA. An absent inventory means unknown historical scope, distinct from a verified empty inventory. The gate will derive uncited files from this inventory and changed-file evidence. An uncited file prevents Ready until a reviewer explicitly records, for that path and head, that it is outside the confirmed criteria, with an attributable explanation. A reviewer may also record that it is within a criterion, but that decision does not replace a missing evidence citation. Skipped files continue to make ingestion partial and cannot be waived through a file disposition. A rename is assessed under its current path; generated-looking and apparently unrelated paths receive no automatic exception.

File dispositions are separate from criterion resolutions, final acceptance, and runtime verification. They remain visible in saved history, and criteria revision or a new head requires new decisions. The core gate and lifecycle implement this rule without Streamlit or GitHub UI dependencies. Streamlit exposes a bounded per-file decision control; automated tests exercise the core and the control.

Legacy v1–v4 records retain their criterion decisions and final-acceptance events, but their missing inventories load as unknown and their gates recompute to Needs Review. No old Ready is restored from citations or an assumed empty file list. Persisted and exported records remain Pydantic-validated.

The existing `scope-expansion` fixture and historical `expected_gate: ready` label remain unchanged. The ordinary benchmark will explicitly report that historical expectation as superseded by the scope rule and will compare the current rule against a separately recorded expectation. New constructed cases and results are stored separately. Frozen R-002 inputs and result remain untouched.

Considered alternatives: a blanket uncited-file acknowledgment is too weak because it does not state a scope decision; always blocking all uncited files is safe but offers no resolution path; inferring irrelevance from path or generated-file appearance would create False Ready. The explicit per-file outside-criteria disposition is the smallest useful fail-closed path.

Stage 3 remains gated by genuine independent use and a separate owner decision. Automated browser actors and constructed cases do not supply that evidence.
