# Validation

Implementation is in progress; no completed production run through this launcher
is claimed yet.

- Host-Docker sibling candidate: Windows Python 3.14, 19 controller/lifecycle and
  public-source tests passed. Real Docker Desktop test verified identical engine
  IDs inside/outside the runner, nonroot socket access, same-path workspace bind
  mounts, no published ports, no privileged engine, and exact temporary resource
  cleanup. Five unrelated running container IDs remained unchanged.
- Previous revision e0581f6: native controller CI passed Windows, Linux and macOS
  (run 35128921090). Actual ephemeral registration/online/removal passed on Windows
  against the app repository using short-lived credentials; updated sibling
  registration/online/removal also passed from a fresh clone. Full application
  pipeline is pending.
- The removed nested-engine prototype is superseded. No physical macOS/Apple
  Silicon or separate Linux-host Docker execution has been exercised. AMD64
  emulation and native controller checks do not prove those environments.

Run `python -B -m unittest discover -s tests -v` for source tests and
`python -B tests/docker-smoke.py` for the isolated synthetic sibling fixture.
The latter starts Docker resources but does not register with GitHub or deploy.
