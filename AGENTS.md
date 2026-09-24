# Release environment

Read README.md, docs/CONTRACT.md and VALIDATION.md before changing this repository.
It is public. No secrets, host addresses, user content or application runtime may
be committed. Credentials belong to GitHub CLI/OS storage or temporary job tokens.
Keep all local generated state under ignored .state/. Never print token values.

Use one shared controller for PowerShell and Bash. Preserve lowercase commands.
Do not add a second application source tree or replace an app's own deployment
adapter. PRs never run on the self-hosted production/local release runners.

Test meaningful lifecycle paths, interrupted/ambiguous operations, wrong identities
and refusal paths before publication. Preserve unrelated Docker resources; no
global prune. Do not claim macOS/ARM validation from Windows or AMD64 tests.

## Disposable resource retention

Remove finished disposable containers, images, networks and synthetic volumes
promptly. Retain only resources in active use or with a concrete near-term use;
record the reason and recheck point. Source published in Git can be rebuilt.
After controller cleanup, inspect remaining runner images and task-owned cache
and remove them by exact identity when finished. Preserve application data,
credentials, tool homes, backups and unrelated active work. No global prune.

Owner clarification September 24: keep the designated VoiceVault local test
environment available as a standing exception, including its container services,
current image and required state. Do not remove it as disposable test output.
Recheck this exception only if the owner retires or replaces that environment.
