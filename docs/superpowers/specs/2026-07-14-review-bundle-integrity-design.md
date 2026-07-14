# Review Bundle Cross-Reference Integrity Design

## Problem

`ReviewBundle` validates each nested object but does not validate relationships between those
objects. A controlled probe showed two concrete failures:

1. A finding can reference an evidence ID that is absent from `bundle.evidence`. The bundle passes
   Pydantic validation, then Markdown export raises `KeyError`.
2. A finding for `AC-01` can reference an evidence item whose own `criterion_id` is `AC-99`. The
   bundle validates and exports that evidence under `AC-01`, creating a false association.

Because review bundles are persisted and exported, nested shape validation alone is insufficient.
Cross-reference integrity belongs in the UI-independent Pydantic boundary.

## Decision

Add one deterministic `ReviewBundle` model validator enforcing this graph:

- criterion IDs are unique;
- evidence IDs are unique and every evidence item belongs to a known criterion;
- finding criterion IDs are unique and exactly match the criterion set;
- each finding's evidence references are unique, resolve to existing evidence, and belong to the
  same criterion as the finding;
- runtime evidence belongs to a known criterion;
- active resolutions have unique criterion IDs and belong to known criteria;
- every criterion reference inside each gate list is unique and belongs to a known criterion.

Validation runs in a stable order and emits stable, field-specific messages. Empty criteria with
empty related collections remain structurally valid; the lifecycle decides whether analysis is
ready.

## Scope boundaries

This change does not recompute findings or gates, require every evidence item to be referenced,
validate URL/SHA formats, enforce nonblank finding prose, change evidence levels, or alter gate
precedence. Those are separate contracts. Overlap between different gate lists is not rejected
because an accepted exception may also be conditional.

## Verification

Regression-first tests cover duplicate identities, missing and extra findings, dangling and
cross-criterion evidence links, duplicate finding references, unknown runtime/resolution/gate
criteria, and duplicate active resolutions/gate references. A valid bundle round trip remains
accepted. Full source, deterministic benchmark, archived-wheel, installed identity, schema probe,
and loopback health checks follow before protected integration.

These controlled checks prove schema and packaging behavior only. They do not establish external
PR runtime evidence, customer validation, or adoption. No billing, paid API or LLM, private
repository, second account, organization, fork test, synthetic validation, or invented evidence is
involved.
