"""Exercise the real host-Docker sibling topology without registering a runner."""
import importlib.util
import json
from pathlib import Path
import time
import uuid
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('release', Path(__file__).resolve().parents[1] / 'scripts/release.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
state = {**m.installation(), 'request': uuid.uuid4().hex, 'mode': 'local',
         'repository': 'example/synthetic', 'runner': 'not-registered', 'revision': 'a' * 40}
before = set(m.command(['docker', 'ps', '--format', '{{.ID}}']).splitlines())
try:
    m.start_runner(state)
    identity = m.compose(state, 'ps', '-q', 'runner')
    details = json.loads(m.command(['docker', 'inspect', identity]))[0]
    assert not details['HostConfig']['PortBindings']
    assert not details['HostConfig']['Privileged']
    assert any(mount['Destination'] == '/var/run/docker.sock' for mount in details['Mounts'])
    host_id = m.command(['docker', 'info', '--format', '{{.ID}}'])
    runner_id = m.compose(state, 'exec', '-T', 'runner', 'gosu', 'runner', 'docker', 'info', '--format', '{{.ID}}')
    assert host_id == runner_id, 'Runner must use the same Docker daemon'
    work = state['work_root']
    m.compose(state, 'exec', '-T', 'runner', 'sh', '-c',
              'mkdir -p "$RELEASE_WORK_ROOT/probe"; printf synthetic-only > "$RELEASE_WORK_ROOT/probe/marker"')
    content = m.compose(state, 'exec', '-T', 'runner', 'docker', 'run', '--rm',
                        '--mount', f'type=bind,src={work}/probe,dst=/probe,readonly',
                        'alpine:3.22', 'cat', '/probe/marker')
    assert content == 'synthetic-only'
    m.compose(state, 'exec', '-T', 'runner', 'docker', 'run', '--rm',
              'alpine:3.22', 'nslookup', 'deb.debian.org')
    print('Host engine identity, nonroot Docker access, sibling bind paths and zero published ports passed.')
finally:
    # No GitHub registration exists in this fixture. Use real resource cleanup.
    with patch.object(m, 'api', return_value={'runners': []}):
        m.cleanup(state)
after = set(m.command(['docker', 'ps', '--format', '{{.ID}}']).splitlines())
assert before == after, 'Unrelated running container identities changed'
print('Temporary containers/work volume removed; cache and unrelated containers preserved.')
