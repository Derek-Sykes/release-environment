# Validation

## Latest selected-snapshot rehearsal

On September 16, 2026, launcher `28bbe2741a5e1af3af1028db0383d9bbbff2ea2a`
completed `release.ps1 local` in
[run 35149582555](https://github.com/Derek-Sykes/VoiceVault/actions/runs/35149582555).
Selected VoiceVault source `9a3f1cba12471c1d1c5475a89f206b666044c7d3` deployed
successfully even though main advanced to documentation-only `2916192` while
testing. Main merges produced no automatic release. Each new command selects a
fresh snapshot; overlapping requests have a separate release-order guard.

Production, development and restricted-agent suites each passed 704 tests, plus
13 populated SQLite checks, Docker persistence, isolated dev/agent workflows,
repository audits, nine pipeline and nineteen server adapter regressions.
The same tested production image was published and deployed by digest:
`sha256:65719d58cda75e812c466e5f4b86400388a2e0c2fcdb92751224c700e3c4d50f`.
Server backup/migration/health/storage checks and independent data-preservation
and live UI observations passed. No GitHub-hosted build jobs ran.

Temporary local runner/network/checkout/release images were removed. Reusable
runner and host build cache remain; unrelated apps remained healthy. Server
retention removed seven unused images automatically. A separate reviewed
child-first legacy cleanup removed 38 obsolete objects, preserving current and
previous releases only. The workflow was paused for that operator cleanup and
re-enabled. No global prune, forced removal or data/volume deletion.

Two preceding attempts stopped safely before publication on transient DNS
failures. Their workspaces cleaned up; a new explicit release performed all gates.
The obsolete moving-main lookup was removed in response to the owner's snapshot
requirement. Network/registry availability still matters. Physical Mac/ARM Docker
and the billing-blocked private hosted route remain unverified. Historical
cross-platform controller and real Linux Docker evidence follows below.

## Previous release and platform evidence


The local release route completed successfully on September 16, 2026. Public
launcher source `c70a318d07b7e676aae3b39e704cbf731ae65b2a` released the exact
VoiceVault main `37b119722f2bdbd1bb400566fb086228d589e4c6` in
[run 35136414842](https://github.com/Derek-Sykes/VoiceVault/actions/runs/35136414842).

- Windows Docker Desktop: `release.ps1 local` registered an ephemeral runner,
  checked out main into a disposable volume, built one production image, tested
  and published that same image. Production, development and restricted-agent
  environments each passed 701 application tests. Thirteen populated SQLite
  migration checks, startup/persistence smoke, repository audits and isolated
  edit/commit/push checks also passed.
- Published digest:
  `sha256:41448727cecf09dedf2971a5fdb99a2c21d9ecb55ac1746c3abf1a0d581f0d40`.
  Existing server runner verified encrypted backup, completed migration checks,
  deployed that digest and verified healthy services with unchanged storage and
  networks. Independent server read and HTTPS health passed. Hosted build jobs
  were skipped; local and server jobs used self-hosted runners.
- Final controller receipt reports success. Temporary runner, network, checkout
  volume and local release image references were removed. Five unrelated local
  apps stayed running. Reusable runner image and host-managed build cache remain.
  Server retention protected current and previous healthy releases and removed
  seven unused owned images. Safety checks retained 44 historical candidates:
  36 are parent images required by protected releases; eight other old image
  objects remain after the conservative pass. This does not claim only two
  image objects in Docker or force removal of dependent layers.
- Public launcher [CI 35136105164](https://github.com/Derek-Sykes/release-environment/actions/runs/35136105164)
  passed 19 controller/lifecycle/public-source tests on Windows, Linux and macOS,
  plus a real Ubuntu Docker sibling-container/cleanup test. Real Windows Docker
  tests independently verified same engine IDs, nonroot socket access, sibling
  bind mounts, private networks and owned image cleanup. Fresh-clone GitHub runner
  registration/online/removal passed.
- Earlier application run 35133222814 passed tests and uploaded its image, but
  positional digest selection stopped deployment. The app now selects and checks
  its exact GHCR digest; five regression fixtures and the successful second run
  verify the correction. The removed nested-engine prototype is superseded.

Limits: private GitHub-hosted release remains unexercised because of account
billing restrictions. Physical macOS/Apple Silicon Docker and native ARM Linux
execution remain unverified; controller CI is not proof of those Docker setups.
One disposable public-tooling verification clone remains ignored locally because
automatic approval review blocked its deletion; its Docker resources were removed.

Run `python -B -m unittest discover -s tests -v` for source tests and
`python -B tests/docker-smoke.py` for the isolated synthetic sibling fixture.
The latter starts Docker resources but does not register with GitHub or deploy.
