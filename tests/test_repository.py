"""Publication guard: inspect tracked/publishable source, never ignored state."""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublicRepositoryTests(unittest.TestCase):
    def test_runtime_is_ignored_and_no_credential_shapes_are_publishable(self):
        ignored = subprocess.run(['git', 'check-ignore', '--quiet', '.state/installation.json'], cwd=ROOT)
        self.assertEqual(0, ignored.returncode)
        output = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT)
        sensitive = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)')
        for name in output.decode().split('\0'):
            if not name:
                continue
            self.assertNotIn('.state', Path(name).parts)
            self.assertNotIn(name.lower(), ('hosts.yml', '.env', 'credentials.json'))
            text = (ROOT / name).read_text(encoding='utf-8')
            self.assertFalse(sensitive.search(text), f'Credential-shaped content in {name}; details withheld')

    def test_powershell_and_shell_entrypoints_exist_in_lowercase(self):
        for name in ('setup', 'release', 'test'):
            for suffix in ('.ps1', '.sh'):
                self.assertTrue((ROOT / (name + suffix)).is_file())


if __name__ == '__main__':
    unittest.main()
