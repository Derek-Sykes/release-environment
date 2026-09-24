# Release environment

Build and test the exact `main` revision of an application on your own computer
or GitHub's runners, publish its tested image to GitHub Container Registry, then
let the application's existing server runner deploy that immutable image.
VoiceVault is preconfigured. This repository contains launchers and build tools;
it does not contain application data, server addresses, passwords or API keys.

## First setup

Install **Git, Python 3.10+, and GitHub CLI**. Local builds additionally require
Docker Desktop in Linux-container mode (Windows/macOS), or Docker Engine with
Compose v2 (Linux). The setup checks these prerequisites and builds the runner;
it does not silently install system software or require Docker for the GitHub route.

```sh
git clone https://github.com/Derek-Sykes/release-environment.git
cd release-environment
```

Windows PowerShell:

```powershell
.\setup.ps1
.\test.ps1               # Test main locally; no publication or deployment
.\release.ps1 local      # Start local builder, test, publish and deploy
.\release.ps1 github     # Build on GitHub; no local Docker needed
```

macOS or Linux:

```sh
./setup.sh
./test.sh
./release.sh local
./release.sh github
```

For GitHub-only setup, use `./setup.sh --github-only` or
`.\setup.ps1 -GitHubOnly`. All command names are lowercase. The local command can
perform its setup lazily, including starting an installed Docker Desktop on
Windows/macOS. On Linux, start your Docker service and grant your user Docker
access through your normal system setup first.

If GitHub CLI is not signed in, the launcher opens its browser/device login.
Complete that flow yourself, including any required two-factor verification.
Your GitHub account password is never collected. GitHub CLI uses the OS credential
store where available; its documented fallback is a local configuration file.
Neither location is in this repository. See `gh auth status` for your installation.
Never paste a password or token into a script, profile or issue.

The GitHub account needs permission to dispatch the application's workflow, and
repository administration permission to register a local runner. Access to this
public launcher repository does not grant access to private application source.

## What happens

1. Resolve GitHub `main` to an exact commit and verify the app's workflow contract.
2. For `local`, start a fresh request-scoped GitHub runner connected to your local Docker engine.
   The runner receives only that request's unique label and temporary credentials.
3. Dispatch the app's workflow. It checks out that commit into disposable storage,
   builds the production image once, and exercises its production checks on either route.
4. A release publishes that tested image to GHCR. Test-only runs never publish or deploy.
5. The existing server runner verifies the selected revision and request order, performs the app's
   backup/migration procedure, deploys by digest and verifies service health. VoiceVault's
   development and agent checks run independently alongside deployment on the build runner.
6. After all jobs finish, the launcher reports their separate results and removes its
   temporary runner, checkout volume and containers. A development failure does not
   undo or obscure a successful production deployment.
   The controller leaves the runner image and host build cache for scoped review.
   Remove finished resources at handoff unless they have a concrete near-term use.

VoiceVault releases are manual: merging dev into main does not publish or deploy.
Run a release command when main is ready. That selects main's exact commit once;
later pushes do not cancel it or change what gets tested/deployed. Start another
release to select newer code. A slower older request cannot overwrite a newer
request that has already deployed. No local Git changes are released.
Neither route merges branches. The server's
data remains on its persistent volumes. An old application image is not a backup
of a database, recordings or configuration.

Local jobs and server deployment jobs use self-hosted runners; they do not consume
GitHub-hosted build minutes. The `github` route does consume hosted minutes for a
private application's builds. Independent PR/dev workflows have their own costs.
The local PC needs to remain awake and online during its build. Once publication
finishes, server deployment does not need a VPN connection from that PC.

## Isolation, resources and recovery

The runner mounts your local Docker socket and creates sibling test containers on
that same engine. There is no nested Docker daemon, privileged engine container,
or extra DNS service. Setup mounts the socket and grants the runner user access
automatically; it does not change the host socket's permissions. Docker access is
powerful: use only trusted application `main` commits. Public pull requests must
never run on this runner. The public launcher has no self-hosted workflow.

A temporary named volume is mounted at the engine's own Linux path so sibling
containers can bind the checked-out source consistently on Docker Desktop and
Linux. Tests join private Docker networks, without publishing test web ports.
The runner itself is limited to 1 CPU/1 GB; sibling builds and tests use Docker's
existing resource limits. Adjust Docker Desktop's memory/CPU settings if needed.
Docker's normal build-cache garbage collection applies; this tool does not change
host-wide cache policy or perform a global prune. Cached source layers stay local.
Temporary checkouts and unused release image references are removed by scoped
cleanup. Afterward, inspect and remove the unused runner image and task-owned
cache by exact identity. Retain them only for active work or a concrete near-term
follow-up, with a reason and recheck point; published source can be rebuilt.
Preserve real application data, credentials, tool homes, backups and unrelated
active work. A designated persistent local test environment is a standing
retention exception: keep its services, current image and required state until
its owner retires or replaces it. Never use an indiscriminate global prune.

The target is Linux AMD64, matching the preconfigured server. Apple Silicon uses
Docker's AMD64 emulation, which can be slower. An ARM Linux machine needs working
AMD64 emulation configured by its administrator. See [validation](VALIDATION.md)
for which platforms have actually been exercised.

If a terminal closes, the job may continue. Reopen this folder and run
`.\release.ps1 resume` or `./release.sh resume`. This follows the existing request
instead of creating another release, then finishes cleanup. `status` displays the
latest request and its GitHub link. An ambiguous dispatch response preserves the
runner rather than risking duplicate deployments or deleting active work.

`.state/` stores this clone's resource identity and small operation receipts. It is
ignored by Git. Do not copy `.state/` to another computer or delete it during a
release; a fresh clone must generate its own identity. Keep this small controller
state; application checkouts are temporary and images/caches follow the scoped
retention rule above.

## Another application

Adding an app only adds a JSON file in `profiles/` and the matching workflow in
that application's repository. No additional service stays running.
Use `./release.sh local --app example` or `.\release.ps1 local -App example`.
See [the workflow contract](docs/CONTRACT.md). Existing app-specific tests, backups,
migrations and server deployment remain owned by that app's repository.

## Development

Run `python -B -m unittest discover -s tests -v`. Keep new tests synthetic; never
commit tokens, credentials, runtime snapshots, private source clones or recordings.
Do not trigger a deployment merely to validate a launcher change.
