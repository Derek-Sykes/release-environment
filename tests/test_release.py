import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('release', Path(__file__).resolve().parents[1] / 'scripts/release.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = patch.object(m, 'STATE', Path(self.temp.name)).start()
        self.addCleanup(patch.stopall)
        self.config = {'repository': 'example/app', 'branch': 'main', 'workflow': 'ci.yml', 'contract': 1}

    def pending(self, **kw):
        return {'instance': 'a' * 12, 'request': 'b' * 32, 'runner': 'release-local-' + 'b' * 32,
                'repository': 'example/app', 'workflow': 'ci.yml', 'mode': 'local',
                'revision': 'c' * 40, **kw}

    def test_profiles_cannot_escape_directory_or_select_another_branch(self):
        for invalid in ('../secret', '/tmp/profile', 'voicevault.json', 'A', 'a/b'):
            with self.subTest(invalid=invalid), self.assertRaises(m.ReleaseError):
                m.profile(invalid)

    def test_main_is_pinned_and_contract_required(self):
        calls = []
        def api(route):
            calls.append(route)
            if '/git/ref/' in route:
                return {'object': {'sha': 'a' * 40}}
            return {'content': base64.b64encode(b'# release-environment-contract: 1').decode()}
        with patch.object(m, 'api', side_effect=api):
            self.assertEqual('a' * 40, m.workflow_revision(self.config))
        self.assertTrue(calls[-1].endswith('?ref=' + 'a' * 40))
        with patch.object(m, 'api', side_effect=[{'object': {'sha': 'a' * 40}}, {'content': base64.b64encode(b'old workflow').decode()}]):
            with self.assertRaises(m.ReleaseError):
                m.workflow_revision(self.config)

    def test_new_clone_gets_independent_persistent_identity(self):
        one = m.installation()
        self.assertEqual(one, m.installation())
        (m.STATE / 'installation.json').unlink()
        self.assertNotEqual(one, m.installation())

    def test_token_transport_does_not_add_windows_carriage_returns(self):
        output = m.command([sys.executable, '-c', 'import sys; print(sys.stdin.buffer.read().hex())'], data=b'synthetic\n')
        self.assertEqual(b'synthetic\n'.hex(), output)

    def test_github_route_does_not_require_docker(self):
        with patch.object(m, 'github_ready'), patch.object(m, 'profile', return_value=self.config), \
             patch.object(m, 'workflow_revision', return_value='a' * 40), \
             patch.object(m, 'prepare_runner', side_effect=AssertionError('Docker must not run')), \
             patch.object(m, 'api') as api, patch.object(m, 'follow'):
            m.main(['github'])
        body = api.call_args.kwargs['body']
        self.assertEqual('main', body['ref'])
        self.assertEqual('github', body['inputs']['build_location'])
        self.assertEqual('', body['inputs']['runner_label'])
        self.assertFalse(body['inputs']['test_only'])

    def test_local_refuses_a_remote_docker_context(self):
        with patch.dict(m.os.environ, {'DOCKER_HOST': 'ssh://example.invalid'}), \
             patch.object(m.shutil, 'which', return_value='/synthetic/docker'), \
             patch.object(m, 'command') as command:
            with self.assertRaisesRegex(m.ReleaseError, 'remote'):
                m.docker_ready()
            command.assert_not_called()

    def test_local_and_test_start_runner_before_dispatch(self):
        for mode, test_only in [('local', False), ('test', True)]:
            (m.STATE / 'active.json').unlink(missing_ok=True)
            events = []
            with patch.object(m, 'github_ready'), patch.object(m, 'profile', return_value=self.config), \
                 patch.object(m, 'workflow_revision', return_value='a' * 40), \
                 patch.object(m, 'prepare_runner', side_effect=lambda s: events.append('runner')), \
                 patch.object(m, 'api', side_effect=lambda *a, **kw: events.append(kw['body'])), \
                 patch.object(m, 'follow'):
                m.main([mode])
            self.assertEqual('runner', events[0])
            self.assertEqual('local', events[1]['inputs']['build_location'])
            self.assertEqual(test_only, events[1]['inputs']['test_only'])

    def test_uncertain_dispatch_retains_state_and_never_retries(self):
        with patch.object(m, 'github_ready'), patch.object(m, 'profile', return_value=self.config), \
             patch.object(m, 'workflow_revision', return_value='a' * 40), \
             patch.object(m, 'api', side_effect=m.ReleaseError('network failure')) as api, \
             patch.object(m, 'cleanup') as cleanup:
            with self.assertRaises(m.ReleaseError):
                m.main(['github'])
            self.assertEqual(1, api.call_count)
            self.assertTrue(m.read('active.json')['dispatch_attempted'])
            cleanup.assert_not_called()
            with self.assertRaisesRegex(m.ReleaseError, 'prior release'):
                m.main(['github'])
            self.assertEqual(1, api.call_count)

    def test_resume_does_not_dispatch_again(self):
        state = self.pending(dispatch_attempted=True, run_id=123)
        m.save('active.json', state)
        with patch.object(m, 'github_ready'), patch.object(m, 'follow') as follow, \
             patch.object(m, 'api', side_effect=AssertionError('No dispatch')):
            m.main(['resume'])
        follow.assert_called_once_with(state)

    def test_discovery_matches_unique_request_not_latest_run(self):
        state = self.pending()
        runs = [{'id': 10, 'display_title': 'Someone else', 'html_url': 'https://example.invalid/wrong'},
                {'id': 11, 'display_title': f"Release {state['request']} (local)", 'html_url': 'https://example.invalid/right'}]
        with patch.object(m, 'api', return_value={'workflow_runs': runs}):
            self.assertEqual(11, m.find_run(state)['id'])
        self.assertEqual(11, m.read('active.json')['run_id'])

    def test_busy_runner_prevents_all_cleanup(self):
        state = self.pending()
        with patch.object(m, 'api', return_value={'runners': [{'id': 1, 'name': state['runner'], 'busy': True}]}), \
             patch.object(m, 'compose') as compose:
            with self.assertRaisesRegex(m.ReleaseError, 'busy'):
                m.cleanup(state)
            compose.assert_not_called()

    def test_interrupted_build_cleanup_preserves_used_or_foreign_images(self):
        state = self.pending()
        identity = 'sha256:' + 'd' * 64
        for foreign, used, expected in [(False, False, True), (True, False, False), (False, True, False)]:
            calls = []
            def compose(_state, *args):
                calls.append(args)
                if 'ls' in args:
                    return identity
                if 'ps' in args:
                    return 'in-use' if used else ''
                if 'inspect' in args:
                    return json.dumps([{'Id': identity, 'RepoTags': ['unrelated:keep' if foreign else 'ghcr.io/example/synthetic:sha-a'],
                                        'Config': {'Labels': {'org.opencontainers.image.source': 'https://github.com/example/synthetic'}}}])
                return ''
            state['repository'] = 'example/synthetic'
            with patch.object(m, 'compose', side_effect=compose):
                m.cleanup_images(state)
            self.assertEqual(expected, any('rm' in args for args in calls))

    def test_cleanup_refuses_foreign_workspace(self):
        state = self.pending()
        inspected = subprocess.CompletedProcess([], 0, json.dumps([{'Labels': {'release-environment.instance': 'someone-else'}}]), '')
        with patch.object(m, 'api', return_value={'runners': []}), patch.object(m, 'compose'), \
             patch.object(m, 'docker_ready'), \
             patch.object(m, 'command', return_value=inspected) as command:
            with self.assertRaisesRegex(m.ReleaseError, 'ownership changed'):
                m.cleanup(state)
            self.assertEqual(1, command.call_count)

    def test_failed_run_is_not_reported_success_and_is_cleaned(self):
        state = self.pending(run_id=11, url='https://example.invalid/run')
        with patch.object(m, 'api', return_value={'status': 'completed', 'conclusion': 'failure'}), \
             patch.object(m, 'cleanup') as cleanup:
            with self.assertRaisesRegex(m.ReleaseError, 'did not succeed'):
                m.follow(state)
        cleanup.assert_called_once()

    def test_existing_login_does_not_prompt_and_missing_login_uses_browser(self):
        ok = subprocess.CompletedProcess([], 0, '', '')
        failed = subprocess.CompletedProcess([], 1, '', '')
        with patch.object(m.shutil, 'which', return_value='/synthetic/gh'), patch.object(m, 'command', return_value=ok) as command:
            m.github_ready()
            self.assertEqual(1, command.call_count)
        with patch.object(m.shutil, 'which', return_value='/synthetic/gh'), patch.object(m, 'command', side_effect=[failed, ok, ok]) as command:
            m.github_ready()
            self.assertIn('--web', command.call_args_list[1].args[0])


if __name__ == '__main__':
    unittest.main()
