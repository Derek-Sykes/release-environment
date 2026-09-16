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
2. For `local`, start an isolated Docker engine and a fresh one-job GitHub runner.
   The runner receives only that request's unique label and temporary credentials.
3. Dispatch the app's workflow. It checks out that commit into disposable storage,
   builds the production image once, and exercises the same checks on either route.
4. A test-only run stops here. A release publishes the exact tested image to GHCR.
5. The existing server runner checks the current revision, performs the app's
   backup/migration procedure, deploys by digest and verifies service health.
6. The launcher removes its temporary runner, checkout volume and containers.
   A bounded Docker build cache and the reusable runner image remain for speed.

No local Git changes are released. Neither route merges branches. The server's
data remains on its persistent volumes. An old application image is not a backup
of a database, recordings or configuration.

Local jobs and server deployment jobs use self-hosted runners; they do not consume
GitHub-hosted build minutes. The `github` route does consume hosted minutes for a
private application's builds. Independent PR/dev workflows have their own costs.
The local PC needs to remain awake and online during its build. Once publication
finishes, server deployment does not need a VPN connection from that PC.

## Isolation, resources and recovery

The builder runs a dedicated Docker-in-Docker daemon. It does **not** mount the
desktop's Docker socket, other application volumes, or your home directory.
Docker-in-Docker requires a privileged engine container: use this only for trusted
application `main` commits. Public pull requests must never run on this runner.
The public launcher repo has no automatically triggered self-hosted workflow.

Default ceilings are 4 CPUs/6 GB for the build engine and 1 CPU/1 GB for the job
runner; these are limits, not constant consumption. Set `RELEASE_CPUS` and
`RELEASE_MEMORY` before invoking a command to adjust the engine. The containers
stop after completion. The dedicated builder has a 10 GB cache GC target; in-use
layers and temporary builds may need additional free disk space. Cache layers can
contain previously built source; they are local disposable build data, not release
history. No cleanup uses a global Docker prune or touches unrelated applications.

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
state, the runner image and caches; application checkouts are temporary.

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
