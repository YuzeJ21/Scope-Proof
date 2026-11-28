# Final v0.2.9 publication review

The owner asked to execute the next stage after PR #308. Prepare freshly built final-version
archives and release notes for a publication decision. Public v0.2.8 remains the default download;
0.2.9 source and its CI packet remain unpublished. Existing development candidates and frozen
examples retain their original bytes and producer identities. No tag, Release, deployment,
outreach, independent-use claim or evidence/gate/schema/dependency change is included.

## Approach

Reuse the exact-source candidate workflow already verified at main f13370dbd1543dffde44e20b6441e0b376fa349b.
Advance the single package version to 0.2.9, align active source documentation, and record
release notes and the source/asset review procedure in a tracked publication-review document.
The existing five-file packet already binds source, archive and installed test observations.
A separate release pipeline or renamed development assets would duplicate this machinery or
break artifact identity. This implementation choice is the executor's, within the requested goal.

## Acceptance

- Fresh archives report 0.2.9; wheel/source metadata and every tested wheel agree.
- The final builder refuses old development archives without changing them or creating output.
- Packet publication remains unpublished, and public-v0.2.8 guidance remains truthful.
- Source/installed/browser/Windows/Python/locked checks pass for the reviewed branch and main.
- The PR records exact main source, run, artifact, archive hashes and remaining publication steps.
- Historical candidates, maintained examples, v9 producer identity and frozen R-002 stay intact.

The package README must describe a publication decision without suggesting that an already
fresh final-version packet needs renaming or another version conversion. Final release notes
live in the tracked review document; CI artifact metadata and checksums are recorded in the PR,
avoiding a second manifest schema. Independent usefulness and repeat use remain unmeasured.
