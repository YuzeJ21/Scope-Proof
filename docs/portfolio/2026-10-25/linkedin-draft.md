# LinkedIn draft — prepared locally, not approved for posting

Green CI tells you that selected checks passed. It does not answer every question in an agreed
acceptance criterion.

I built ScopeProof to make that gap inspectable. A reviewer confirms the exact criteria, then
ScopeProof maps candidate implementation and test lines to each one. It shows missing support,
keeps observed CI and externally supplied runtime records separate, and leaves acceptance with
the human reviewer.

The latest unreleased `0.2.4.dev0` engineering draft strengthens that trust boundary. It checks
mutable GitHub PR data against a comparison pinned to the exact base and head commits, and it
rejects saved review records whose evidence and findings disagree. A deliberately constructed,
installed-app browser walkthrough covers criteria confirmation, evidence, missing evidence,
reviewer controls, and export. It is engineering verification, not customer validation.

ScopeProof never executes the target repository. The published install is still v0.2.3; these
changes are a draft for review at source commit
`47ebc4f275b9f307c9305af3890782fa7578dff4`.

Repository: https://github.com/YuzeJ21/Scope-Proof

The workflow and positioning still need genuine independent use before any adoption or value
claim. The project is available for evaluation under its published use policy, which does not
grant an open-source license.

Publication requires a separate owner decision and a fresh check of the release, PR, and source
status. No post was made as part of this package.
