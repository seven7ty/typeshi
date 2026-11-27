import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_generation import import_declaration


class CliTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.src = Path(temp.name, 'rows.json')
        self.out = Path(temp.name, 'schema.py')
        self.src.write_text('[{"id": 1}, {"id": 2, "flag": true}]')

    def invoke(self, *args):
        return subprocess.run([sys.executable, '-m', 'typeshi', str(self.src), '--name', 'Row', *args],
                              capture_output=True, text=True)

    def test_generation_and_stdout_match(self):
        stdout = self.invoke('--no-literals')
        self.assertEqual(stdout.returncode, 0, stdout.stderr)
        written = self.invoke('--no-literals', '-o', self.out)
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertEqual(self.out.read_text(), stdout.stdout)
        self.assertEqual(import_declaration(self.out).Row.__annotations__['id'], int)
        self.assertEqual(import_declaration(self.out).Row.__optional_keys__, {'flag'})

    def test_check_missing_current_and_stale_never_writes(self):
        args = ('-o', self.out, '--check')
        missing = self.invoke(*args)
        self.assertEqual(missing.returncode, 1, missing.stderr)
        self.assertIn('missing', missing.stderr)
        self.assertFalse(self.out.exists())
        self.assertEqual(self.invoke('-o', self.out).returncode, 0)
        original = self.out.read_bytes()
        self.out.write_bytes(original.replace(b'\n', b'\r\n'))
        before = self.out.stat().st_mtime_ns
        check = self.invoke(*args)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertEqual(self.out.stat().st_mtime_ns, before)
        self.src.write_text('{"new": 1}')
        stale = self.invoke(*args)
        self.assertEqual(stale.returncode, 1, stale.stderr)
        self.assertIn('stale', stale.stderr)
        self.assertEqual(self.out.read_bytes(), original.replace(b'\n', b'\r\n'))
        self.assertEqual(self.out.stat().st_mtime_ns, before)

    def test_input_errors_keep_existing_output(self):
        self.out.write_text('original')
        for invalid in ('{', '[]', '[{}, 1]', 'null'):
            self.src.write_text(invalid)
            for extra in [[], ['--check']]:
                with self.subTest(invalid=invalid, extra=extra):
                    result = self.invoke('-o', self.out, *extra)
                    self.assertEqual(result.returncode, 2)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertEqual(self.out.read_text(), 'original')

    def test_usage_and_same_file_errors(self):
        self.assertEqual(self.invoke('--check').returncode, 2)
        original = self.src.read_bytes()
        os.link(self.src, self.out)
        result = self.invoke('-o', self.out)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.src.read_bytes(), original)
