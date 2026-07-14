# Resolution Event Boundary Design

## Problem

`append_resolution()` revalidates its input state but does not validate that an
active analysis exists or that a criterion event targets the active criterion
set. It can return an invalid active bundle containing a resolution for an
unknown criterion; only a later persistence or export revalidation catches it.

## Decision

The lifecycle command will fail closed before binding or appending an event:

- reconstruct the supplied event through its Pydantic schema so validator-bypassing
  mutations cannot affect gate state;
- an active analysis bundle is required for criterion decisions and final
  acceptance events;
- criterion decisions must reference a criterion in that active bundle;
- final acceptance events remain review-level events with no criterion ID.

Revision binding also reconstructs the event through the schema instead of using
unchecked model copying.

The Pydantic event shape, append-only history, latest-event semantics, and gate
evaluation remain unchanged.

## Verification

Regression tests call the real lifecycle function with a bundleless confirmed
revision, an unknown criterion, and a valid-then-mutated event that would otherwise
make an accepted review Ready. Existing valid criterion and final-acceptance flows
must remain green, followed by the full suite, Ruff, benchmark, clean-wheel smoke,
and independent review.
