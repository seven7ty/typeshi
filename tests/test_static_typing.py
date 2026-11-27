import subprocess
import sys
import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path

from typeshi import declaration_module_from_typeddict, typeddict_from_dict


class StaticTypingTests(unittest.TestCase):
    @unittest.skipUnless(find_spec('mypy'), 'install mypy to check a generated module and its consumer')
    def test_mypy_accepts_generated_schema_and_infers_field_types(self):
        td = typeddict_from_dict('Payload', {
            'fields': {'is-ready': True},
            'items': [1, 'two'],
            'records': [{'id': 1}, {'id': 'two', 'note': 'ok'}],
        }, literals_where_possible=True)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'schema.py').write_text(declaration_module_from_typeddict(td), encoding='utf-8')
            (root / 'consumer.py').write_text(
                'from typing import Literal, assert_type\n'
                'from schema import Payload\n\n'
                'def verify(payload: Payload) -> None:\n'
                '    assert_type(payload["fields"]["is-ready"], Literal[True])\n'
                '    assert_type(payload["items"], list[int | str])\n'
                '    row = payload["records"][0]\n'
                '    assert_type(row["id"], Literal[1, "two"])\n'
                '    if "note" in row:\n'
                '        assert_type(row["note"], Literal["ok"])\n',
                encoding='utf-8',
            )
            result = subprocess.run([sys.executable, '-m', 'mypy', '--strict', 'schema.py', 'consumer.py'],
                                    cwd=root, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
