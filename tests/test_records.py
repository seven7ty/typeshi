import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Literal, NotRequired, get_args, get_type_hints, is_typeddict

from typeshi import save_declaration_module_from_json, typeddict_from_dict, typeddict_from_records
from test_generation import import_declaration, round_trip


class RecordTests(unittest.TestCase):
    def test_missing_nullable_and_conflicting_fields(self):
        rows = iter([{'id': 1, 'nickname': None}, {'id': 'two', 'nickname': 'Ann'}, {'id': 3}])
        td = typeddict_from_records('User', rows)
        for schema in td, round_trip(td):
            self.assertEqual(schema.__required_keys__, {'id'})
            self.assertEqual(schema.__optional_keys__, {'nickname'})
            self.assertEqual(get_type_hints(schema, include_extras=True),
                             {'id': int | str, 'nickname': NotRequired[str | None]})

    def test_nested_objects_and_arrays_merge_at_each_path(self):
        rows = [
            {'profile': {'aliases': []}, 'items': [None, {'details': {'price': 10}}]},
            {'profile': {'aliases': ['a'], 'city': 'Lima'}, 'items': [{'details': {'sku': 'X'}}, {}]},
            {'items': []},
        ]
        schema = round_trip(typeddict_from_records('Order', rows))
        self.assertEqual(schema.__optional_keys__, {'profile'})
        profile = get_type_hints(schema)['profile']
        self.assertEqual(profile.__optional_keys__, {'city'})
        self.assertEqual(profile.__annotations__['aliases'], list[str])
        union = get_args(schema.__annotations__['items'])[0]
        self.assertIn(type(None), get_args(union))
        item = next(hint for hint in get_args(union) if is_typeddict(hint))
        self.assertEqual(item.__optional_keys__, {'details'})
        details = get_type_hints(item)['details']
        self.assertEqual(details.__optional_keys__, {'price', 'sku'})

    def test_list_nesting_and_empty_observations(self):
        schema = round_trip(typeddict_from_dict('Root', {'groups': [[], [{'a': 1}], [{'b': 2}]], 'empty': [[]]}))
        group = get_args(get_args(schema.__annotations__['groups'])[0])[0]
        self.assertEqual(group.__optional_keys__, {'a', 'b'})
        self.assertEqual(schema.__annotations__['empty'], list[list[Any]])

    def test_total_false_hooks_and_literal_deduplication(self):
        calls = []

        def name(path, sample):
            calls.append((path, sample))
            return 'Child'

        rows = [{'n': 1, 'ok': True, 'items': [{'a': 1}]}, {'n': 'two', 'ok': True, 'items': [{'b': 2}]}]
        td = typeddict_from_records('Row', rows, total=False, literals_where_possible=True,
                                    type_hooks={int: lambda t, v: float}, nested_typeddict_cls_name_hook=name)
        self.assertEqual(td.__optional_keys__, {'n', 'ok', 'items'})
        self.assertEqual(calls, [(('items', 'item'), {'a': 1})])
        hints = get_type_hints(round_trip(td))
        self.assertEqual(hints['n'], float | Literal['two'])
        self.assertEqual(hints['ok'], Literal[True])
        child = get_args(hints['items'])[0]
        self.assertEqual(child.__required_keys__, set())
        self.assertEqual(child.__annotations__, {'a': float, 'b': float})

    def test_list_hooks_take_precedence(self):
        rows = [{'items': [{'id': 1}]}]
        td = typeddict_from_records('Row', rows, type_hooks={list: lambda t, v: tuple[str, ...]})
        self.assertEqual(td.__annotations__, {'items': tuple[str, ...]})
        td = typeddict_from_records('Row', rows, include_builtin_type_hooks=False)
        self.assertEqual(td.__annotations__, {'items': list})

    def test_cycles_shared_objects_and_invalid_samples(self):
        child = {'id': 1}
        schema = typeddict_from_records('Root', [child, {'children': [child, child]}])
        self.assertEqual(schema.__optional_keys__, {'id', 'children'})
        cycle = []
        cycle.append({'cycle': cycle})
        with self.assertRaisesRegex(ValueError, 'Cyclic'):
            typeddict_from_records('Root', [{'items': cycle}])
        for records, error in [([], ValueError), ([{}, 1], TypeError), ({}, TypeError), ('', TypeError),
                               ([{'items': [{1: 2}]}], TypeError)]:
            with self.subTest(records=records), self.assertRaises(error):
                typeddict_from_records('Root', records)
        self.assertEqual(typeddict_from_records('Empty', [{}, {}]).__annotations__, {})

    def test_json_file_with_a_record_array(self):
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory, 'records.json')
            dest = Path(directory, 'schema.py')
            src.write_text(json.dumps([{'name': 'A'}, {}]))
            save_declaration_module_from_json('Record', src, dest)
            schema = import_declaration(dest).Record
            self.assertEqual(schema.__annotations__, {'name': NotRequired[Literal['A']]})
