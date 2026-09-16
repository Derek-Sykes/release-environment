#!/usr/bin/env python3
"""Dispatch an application's main release, optionally supplying one local runner.

GitHub credentials remain in gh's credential store. Registration tokens are passed
over stdin and never saved in Compose, source, command history or the state file.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.state'


class ReleaseError(RuntimeError):
    pass


def command(args, *, data=None, capture=True, env=None, check=True):
    binary = isinstance(data, bytes)
    result = subprocess.run(args, input=data, text=not binary, encoding=None if binary else 'utf-8',
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None,
                            env=env, cwd=ROOT, check=False)
    if binary:
        if result.stdout is not None:
            result.stdout = result.stdout.decode('utf-8')
        if result.stderr is not None:
            result.stderr = result.stderr.decode('utf-8')
    if check and result.returncode:
        # API responses and Docker commands can contain private connection details.
        raise ReleaseError(f'{Path(str(args[0])).name} could not complete {args[1] if len(args)>1 else "the command"} (exit {result.returncode}).')
    return result.stdout.strip() if capture and check else result


def api(route, *, method='GET', body=None):
    args = ['gh', 'api', '--hostname', 'github.com', '--method', method, route]
    if body is not None:
        args += ['--input', '-']
    output = command(args, data=json.dumps(body) if body is not None else None)
    return json.loads(output) if output else None


def save(name, data):
    STATE.mkdir(exist_ok=True)
    path = STATE / name
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def read(name):
    path = STATE / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def profile(app):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', app):
        raise ReleaseError('Invalid application profile name.')
    path = ROOT / 'profiles' / (app + '.json')
    if not path.is_file():
        raise ReleaseError(f'No profile for {app}. Add profiles/{app}.json using the documented contract.')
    data = json.loads(path.read_text(encoding='utf-8'))
    if (data.get('contract') != 1 or data.get('branch') != 'main'
        or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', data.get('repository', ''))
        or not re.fullmatch(r'[A-Za-z0-9_.-]+\.ya?ml', data.get('workflow', ''))):
        raise ReleaseError('The profile must name a repository, main branch and contract-1 workflow.')
    return data


def github_ready():
    if not shutil.which('gh'):
        raise ReleaseError('Install GitHub CLI, then run gh auth login --hostname github.com.')
    result = command(['gh', 'auth', 'status', '--hostname', 'github.com'], check=False)
    if result.returncode:
        print('Sign in to GitHub in your browser. GitHub CLI will remember the authorization on this computer.', flush=True)
        command(['gh', 'auth', 'login', '--hostname', 'github.com', '--git-protocol', 'https', '--web'], capture=False)
        command(['gh', 'auth', 'status', '--hostname', 'github.com'])


def docker_ready():
    if not shutil.which('docker'):
        raise ReleaseError('Install Docker Desktop with Linux containers before using local.')
    endpoint = os.environ.get('DOCKER_HOST') if not os.environ.get('DOCKER_CONTEXT') else None
    endpoint = endpoint or command(['docker', 'context', 'inspect', '--format', '{{.Endpoints.docker.Host}}'])
    if not endpoint.startswith(('unix://', 'npipe://')):
        raise ReleaseError('The selected Docker context is remote. Select your local Docker engine before using local.')
    def ready():
        result = command(['docker', 'info', '--format', '{{.OSType}}'], check=False)
        return result.returncode == 0 and result.stdout.strip() == 'linux'
    if not ready() and os.name == 'nt':
        candidates = [Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/DockerDesktop/Docker Desktop.exe',
                      Path(os.environ.get('ProgramFiles', '')) / 'Docker/Docker/Docker Desktop.exe']
        desktop = next((p for p in candidates if p.is_file()), None)
        if desktop:
            print('Starting Docker Desktop; waiting for the Linux engine...', flush=True)
            # Path is a discovered executable; pass it as an environment variable,
            # never interpolate a host path into PowerShell source.
            command(['powershell.exe', '-NoProfile', '-Command',
                     'Start-Process -FilePath $env:RELEASE_DOCKER_DESKTOP -WindowStyle Hidden'],
                    env={**os.environ, 'RELEASE_DOCKER_DESKTOP': str(desktop)})
            for _ in range(90):
                if ready():
                    break
                time.sleep(2)
    if not ready() and sys.platform == 'darwin':
        command(['open', '-g', '-a', 'Docker'])
        for _ in range(90):
            if ready():
                break
            time.sleep(2)
    if not ready():
        raise ReleaseError('Docker is not ready in Linux-container mode. Start it and retry.')
    command(['docker', 'compose', 'version'])
    # Desktop's client socket/named pipe differs from its Linux VM socket.
    info = json.loads(command(['docker', 'info', '--format', '{{json .}}']))
    return ('/var/run/docker.sock' if os.name == 'nt' or sys.platform == 'darwin'
            or 'docker desktop' in info.get('OperatingSystem', '').lower()
            else endpoint.removeprefix('unix://'))


def installation():
    config = read('installation.json')
    if config is None:
        config = {'instance': uuid.uuid4().hex[:12]}
        save('installation.json', config)
    if not re.fullmatch(r'[0-9a-f]{12}', config.get('instance', '')):
        raise ReleaseError('Invalid installation identity; preserve .state and inspect it.')
    return config


def compose(state, *args, data=None, capture=True, check=True):
    env = {**os.environ, 'RELEASE_INSTANCE': state['instance'], 'RELEASE_REQUEST': state['request'],
           'RELEASE_WORK_ROOT': state.get('work_root', '/opt/runner/_work'),
           'RELEASE_DOCKER_SOCKET': state.get('docker_socket', '/var/run/docker.sock')}
    return command(['docker', 'compose', '--project-name', 'release-env-' + state['instance'],
                    '--file', str(ROOT / 'compose.yml'), *args],
                   data=data, capture=capture, env=env, check=check)


def start_runner(state):
    state['docker_socket'] = docker_ready()
    print('Preparing one-job runner on the local Docker engine...', flush=True)
    compose(state, 'build', 'runner', capture=False)
    state['local_started'] = True
    save('active.json', state)
    volume = 'release-environment-work-' + state['request']
    command(['docker', 'volume', 'create', '--label', 'release-environment.instance=' + state['instance'],
             '--label', 'release-environment.request=' + state['request'], volume])
    inspected = json.loads(command(['docker', 'volume', 'inspect', volume]))[0]
    labels = inspected.get('Labels') or {}
    if (labels.get('release-environment.instance') != state['instance']
        or labels.get('release-environment.request') != state['request']):
        raise ReleaseError('Temporary workspace ownership changed; refusing to mount it.')
    state['work_root'] = inspected['Mountpoint']
    if not state['work_root'].startswith('/') or '..' in state['work_root'].split('/'):
        raise ReleaseError('Docker returned an invalid workspace mount point.')
    save('active.json', state)
    compose(state, 'up', '--detach', 'runner', capture=False)
    for _ in range(60):
        result = compose(state, 'exec', '-T', 'runner', 'gosu', 'runner', 'docker', 'info', check=False)
        if result.returncode == 0:
            break
        time.sleep(2)
    else:
        raise ReleaseError('The runner could not access the local Docker engine.')


def prepare_runner(state):
    start_runner(state)
    registration = api(f"repos/{state['repository']}/actions/runners/registration-token", method='POST')
    # config.sh consumes a short-lived registration token. It is never an
    # environment variable in Docker's stored container configuration.
    compose(state, 'exec', '-T', 'runner', 'gosu', 'runner', 'sh', '-c',
            'IFS= read -r registration; ./config.sh --unattended --ephemeral --url "$1" '
            '--name "$2" --labels "release-builder,$2" --work "$RELEASE_WORK_ROOT" --token "$registration"',
            'register', 'https://github.com/' + state['repository'], state['runner'],
            data=(registration['token'] + '\n').encode('utf-8'))
    for _ in range(60):
        runners = api(f"repos/{state['repository']}/actions/runners?per_page=100")['runners']
        match = next((r for r in runners if r['name'] == state['runner']), None)
        if match:
            state['runner_id'] = match['id']
            save('active.json', state)
        if match and match['status'] == 'online':
            return
        time.sleep(2)
    raise ReleaseError('The runner did not connect to GitHub; its state was retained for inspection.')


def workflow_revision(config):
    repo = config['repository']
    commit = api(f'repos/{repo}/git/ref/heads/main')['object']['sha']
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ReleaseError('GitHub did not return a valid main revision.')
    workflow = api(f"repos/{repo}/contents/.github/workflows/{config['workflow']}?ref={commit}")
    content = base64.b64decode(workflow['content']).decode('utf-8')
    if '# release-environment-contract: 1' not in content:
        raise ReleaseError('This application has not integrated release-environment contract 1 on main yet.')
    return commit


def find_run(state):
    for _ in range(45):
        response = api(f"repos/{state['repository']}/actions/workflows/{state['workflow']}/runs?event=workflow_dispatch&per_page=100")
        matches = [r for r in response['workflow_runs']
                   if r.get('display_title') == f"Release {state['request']} ({state['mode']})"]
        if len(matches) > 1:
            raise ReleaseError('Multiple workflow runs have this request identity; inspect Actions before retrying.')
        if matches:
            state['run_id'] = matches[0]['id']
            state['url'] = matches[0]['html_url']
            save('active.json', state)
            return matches[0]
        time.sleep(2)
    raise ReleaseError('GitHub has not exposed the dispatched run yet. Use .\\release.ps1 resume; do not dispatch it twice.')


def cleanup_images(state):
    """Remove only this request's unused images, preserving all foreign aliases."""
    source = 'https://github.com/' + state['repository']
    ids = compose(state, 'exec', '-T', 'runner', 'docker', 'image', 'ls', '--quiet', '--no-trunc',
                  '--filter', 'label=org.opencontainers.image.source=' + source,
                  '--filter', 'label=release-environment.request=' + state['request']).splitlines()
    package = 'ghcr.io/' + state['repository'].lower()
    local_prefix = state['repository'].split('/')[1].lower() + '-release:'
    for identity in set(ids):
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', identity):
            raise ReleaseError('Builder returned an invalid image identity; cleanup stopped.')
        used = compose(state, 'exec', '-T', 'runner', 'docker', 'ps', '--all', '--quiet', '--filter', 'ancestor=' + identity)
        if used:
            continue
        item = json.loads(compose(state, 'exec', '-T', 'runner', 'docker', 'image', 'inspect', identity))[0]
        tags = item.get('RepoTags') or []
        digests = item.get('RepoDigests') or []
        if (item.get('Id') != identity or (item.get('Config', {}).get('Labels') or {}).get('org.opencontainers.image.source') != source
            or (item.get('Config', {}).get('Labels') or {}).get('release-environment.request') != state['request']
            or any(not (ref.startswith(package + ':sha-') or ref.startswith(local_prefix)) for ref in tags)
            or any(not ref.startswith(package + '@sha256:') for ref in digests)):
            continue
        for ref in tags or [identity]:
            compose(state, 'exec', '-T', 'runner', 'docker', 'image', 'rm', '--no-prune', ref)


def cleanup(state):
    if state['mode'] == 'local' and state.get('local_started', True):
        # Never stop a busy registration. An ephemeral runner normally removes
        # itself automatically when the build job finishes.
        runners = api(f"repos/{state['repository']}/actions/runners?per_page=100")['runners']
        runner = next((r for r in runners if r['name'] == state['runner']), None)
        if runner and runner.get('busy'):
            raise ReleaseError('The build runner is still busy; cleanup deferred. Use resume later.')
        if runner:
            api(f"repos/{state['repository']}/actions/runners/{runner['id']}", method='DELETE')
        docker_ready()
        running = compose(state, 'ps', '--status', 'running', '--services')
        if 'runner' in running.splitlines():
            cleanup_images(state)
        compose(state, 'down', '--remove-orphans', capture=False)
        volume = 'release-environment-work-' + state['request']
        inspected = command(['docker', 'volume', 'inspect', volume], check=False)
        if inspected.returncode == 0:
            labels = json.loads(inspected.stdout)[0].get('Labels') or {}
            if (labels.get('release-environment.instance') != state['instance']
                or labels.get('release-environment.request') != state['request']):
                raise ReleaseError('Temporary workspace ownership changed; refusing cleanup.')
            command(['docker', 'volume', 'rm', volume])
    save('last.json', {k: state[k] for k in ('repository', 'revision', 'mode', 'run_id', 'url', 'conclusion') if k in state})
    (STATE / 'active.json').unlink(missing_ok=True)


def follow(state):
    if not state.get('run_id'):
        find_run(state)
    print(state['url'], flush=True)
    last = None
    while True:
        run = api(f"repos/{state['repository']}/actions/runs/{state['run_id']}")
        status = (run['status'], run.get('conclusion'))
        if status != last:
            print('Release: ' + ' / '.join(str(v) for v in status if v), flush=True)
            last = status
        if run['status'] == 'completed':
            state['conclusion'] = run['conclusion']
            save('active.json', state)
            cleanup(state)
            if run['conclusion'] != 'success':
                raise ReleaseError('The release did not succeed. See the GitHub run for the failed stage; no automatic database rollback was attempted.')
            return
        time.sleep(10)


@contextlib.contextmanager
def lock():
    STATE.mkdir(exist_ok=True)
    path = STATE / 'controller.lock'
    handle = path.open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            if path.stat().st_size == 0:
                handle.write(b'0'); handle.flush(); handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise ReleaseError('Another release command is already running in this clone.') from None
    try:
        yield
    finally:
        handle.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['local', 'github', 'test', 'setup', 'status', 'resume'])
    parser.add_argument('--app', default='voicevault')
    parser.add_argument('--github-only', action='store_true')
    args = parser.parse_args(argv)
    github_ready()
    if args.mode == 'status':
        state = read('active.json') or read('last.json')
        print(json.dumps(state or {'status': 'No release has been requested from this clone.'}, indent=2))
        return
    with lock():
        if args.mode == 'setup':
            state = {**installation(), 'request': uuid.uuid4().hex}
            if not args.github_only:
                docker_ready()
                compose(state, 'build', 'runner', capture=False)
            print('Setup checks passed. Use .\\release.ps1 local or .\\release.ps1 github.')
            return
        active = read('active.json')
        if args.mode == 'resume':
            if not active:
                raise ReleaseError('No pending release to resume.')
            if active.get('dispatch_attempted'):
                follow(active)
            else:
                cleanup(active)
                print('Interrupted setup cleaned up. You can now request a new release.')
            return
        if active:
            raise ReleaseError('A prior release is pending. Use .\\release.ps1 resume to finish it first.')
        config = profile(args.app)
        revision = workflow_revision(config)
        request = uuid.uuid4().hex
        state = {**installation(), **config, 'revision': revision,
                 'mode': 'local' if args.mode == 'test' else args.mode, 'test_only': args.mode == 'test',
                 'request': request, 'runner': 'release-local-' + request, 'local_started': False}
        save('active.json', state)
        print(f"Releasing {state['repository']} main at {revision} using {args.mode}.", flush=True)
        try:
            if state['mode'] == 'local':
                prepare_runner(state)
            state['dispatch_attempted'] = True
            save('active.json', state)
            api(f"repos/{state['repository']}/actions/workflows/{state['workflow']}/dispatches", method='POST', body={
                'ref': 'main', 'inputs': {'build_location': state['mode'], 'request_id': request,
                                        'expected_sha': revision,
                                        'test_only': state['test_only'],
                                        'runner_label': state['runner'] if state['mode'] == 'local' else ''}})
            follow(state)
        except BaseException:
            # An uncertain HTTP outcome must never cause duplicate dispatch or
            # destroy a runner that may already have received its job.
            if not state.get('dispatch_attempted'):
                cleanup(state)
            else:
                print('If the run is still pending, use .\\release.ps1 resume to follow it and finish cleanup.', flush=True)
            raise


if __name__ == '__main__':
    try:
        main()
    except (ReleaseError, OSError, ValueError) as exc:
        print('Release stopped: ' + str(exc), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Monitoring stopped. The release may continue; use .\\release.ps1 resume.', file=sys.stderr)
        sys.exit(130)
