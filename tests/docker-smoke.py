"""Exercise the real isolated Docker topology without registering a runner."""
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
    m.compose(state, 'up', '--detach', 'engine', 'runner', capture=False)
    for _ in range(90):
        result = m.compose(state, 'exec', '-T', 'runner', 'docker', 'info', check=False)
        if result.returncode == 0:
            break
        time.sleep(2)
    else:
        raise RuntimeError('Isolated Docker did not start')
    for service in ('runner', 'engine'):
        identity = m.compose(state, 'ps', '-q', service)
        details = json.loads(m.command(['docker', 'inspect', identity]))[0]
        assert not details['HostConfig']['PortBindings']
        assert all(mount['Destination'] != '/var/run/docker.sock' for mount in details['Mounts'])
    m.compose(state, 'exec', '-T', 'runner', 'sh', '-c',
              'mkdir -p /opt/runner/_work/probe; printf synthetic-only > /opt/runner/_work/probe/marker')
    content = m.compose(state, 'exec', '-T', 'runner', 'docker', 'run', '--rm',
                        '--mount', 'type=bind,src=/opt/runner/_work/probe,dst=/probe,readonly',
                        'alpine:3.22', 'cat', '/probe/marker')
    assert content == 'synthetic-only'
    print('Isolated engine, shared temporary bind paths, CLI and zero published ports passed.')
finally:
    # No GitHub registration exists in this fixture. Use real resource cleanup.
    with patch.object(m, 'api', return_value={'runners': []}):
        m.cleanup(state)
after = set(m.command(['docker', 'ps', '--format', '{{.ID}}']).splitlines())
assert before == after, 'Unrelated running container identities changed'
print('Temporary containers/work volume removed; cache and unrelated containers preserved.')
