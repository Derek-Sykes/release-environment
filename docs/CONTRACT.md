# Application workflow contracts

An application profile names `repository`, `branch: main`, `workflow` (a YAML
filename), and `contract: 1` or `contract: 2`. The public launcher is generic; it does not discover
or rewrite server configuration and cannot grant itself access to an application.

The app's workflow on main must include a matching `# release-environment-contract: 2` (or `1`) and
accept `workflow_dispatch` inputs:

- `build_location`: `local` or `github`.
- `request_id`: a unique request identifier.
- `expected_sha`: the exact 40-character main commit selected before dispatch.
- `runner_label`: unique `release-local-<request_id>` label for local jobs.
- `test_only`: boolean; tests must not publish or deploy when true.

Its dispatched run name is `Release <request_id> (<build_location>)` so an uncertain
dispatch can be resumed without launching another run. Check out `expected_sha`
explicitly in every release job. Validate its ancestry against the main commit at
dispatch; later main commits do not change the selected version. Dispatches targeting any
branch except main must not run local build, publication or deployment jobs.

Local jobs require all labels `self-hosted`, `linux`, `x64`, `release-builder`
and the request's unique label. Contract 1 supplies an ephemeral one-job runner.
Contract 2 keeps that request-scoped runner registered until the whole workflow
finishes, allowing sequential local jobs. The launcher then unregisters and
removes it. Resume an interrupted controller to follow the same run and finish
cleanup; never start a replacement request while it remains active.

VoiceVault uses contract 2: production image checks/publication finish first;
development/agent validation then reuses the local runner while the separate
server runner deploys. Both jobs depend only on publication, so a development
failure remains visible without blocking or rolling back production. The final
receipt records each job's result. Hosted jobs must be skipped on the local route.
A test-only run must not receive server credentials, publish or deploy.

Use temporary `GITHUB_TOKEN` credentials with minimal permissions. Do not request
Git write or branch-merging authority. Test-only code should never publish. Build
one production image, verify it, and publish the same image by digest. Development
environment checks may build their own distinct development image.

Keep mutation-safe backup/migration and health gates in the server adapter, plus
one deployment concurrency group shared by automatic pushes and both manual
routes. Preserve the selected revision through publication and cutover; do not
recheck a moving main ref or fail merely because new code arrived. Guard request
ordering separately: VoiceVault records its workflow run number in image labels
and rejects an older request after a newer one deployed. Never infer readiness
from a mutable tag or blindly roll back a database with an old application image.

Clean up exact task-owned resources on success and failure. Leave small logs and
results in GitHub; private application data must never become build artifacts.
Separate source-controlled scripts from runner state, application data and cache.

VoiceVault's adapter lives in VoiceVault itself. This repository deliberately does
not copy VoiceVault's application source, tests or production secrets.

## Local Docker topology

The runner controls the host Docker engine through its socket. Application tests
must use request-unique container/project/image identities, bind paths under the
provided workspace/TMPDIR, and private test-network access instead of assuming
that the runner's localhost is the Docker host. VoiceVault's network helper joins
and leaves the runner on its temporary Compose test network. No test web ports
are published in this mode. Labels and exact ownership checks govern cleanup;
never use global image/container/volume pruning. Host-managed build cache remains.
