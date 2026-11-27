import importlib.util
import json
import os
import sys
import tempfile
import unittest
import warnings
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Callable, Literal, NotRequired, Required, TypedDict, get_args, get_type_hints
from unittest.mock import patch

from frozendict import frozendict

from typeshi import (
    __version__, declaration_module_from_typeddict, save_declaration_module_from_json, typeddict_from_dict,
)


class Address(TypedDict):
    city: str


class OptionalBase(TypedDict, total=False):
    id: int


class Record(OptionalBase):
    address: Address
    previous: list[Address]
    tags: NotRequired[list[str]]
    code: Required[Literal['A', 'B']]
    created: date | None


def import_declaration(path):
    spec = importlib.util.spec_from_file_location('generated_schema', path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {spec.name: module}):
        spec.loader.exec_module(module)
    return module


def round_trip(schema, **options):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory, 'schema.py')
        path.write_text(declaration_module_from_typeddict(schema, **options), encoding='utf-8')
        return getattr(import_declaration(path), schema.__name__)


class InferenceTests(unittest.TestCase):
    def test_real_fields_and_total_propagate(self):
        td = typeddict_from_dict('Root', {'fields': {'fields': 1}}, total=False)
        child = td.__annotations__['fields']
        self.assertEqual(child.__annotations__, {'fields': int})
        self.assertEqual(td.__optional_keys__, {'fields'})
        self.assertEqual(child.__optional_keys__, {'fields'})
        saved = round_trip(td)
        self.assertEqual(saved.__annotations__['fields'].__optional_keys__, {'fields'})

    def test_equal_nested_dicts_report_their_own_paths(self):
        paths = []

        def name(path, data):
            paths.append(path)
            self.assertIsInstance(data, dict)
            return '_'.join(path)

        shared = {'leaf': {}}
        td = typeddict_from_dict('Root', {'left': shared, 'right': shared}, nested_typeddict_cls_name_hook=name)
        self.assertEqual(paths, [('left',), ('left', 'leaf'), ('right',), ('right', 'leaf')])
        self.assertEqual(round_trip(td).__annotations__['right'].__annotations__['leaf'].__name__, 'right_leaf')

    def test_custom_hooks_override_defaults_without_mutating_the_mapping(self):
        hooks = {int: lambda t, v: float}
        for mapping in (hooks, frozendict(hooks)):
            with self.subTest(mapping=type(mapping)):
                td = typeddict_from_dict('Row', {'n': 1, 'tags': ['a'], 'b': True}, type_hooks=mapping,
                                         literals_where_possible=True)
                self.assertEqual(td.__annotations__, {'n': float, 'tags': list[str], 'b': Literal[True]})
                self.assertEqual(set(mapping), {int})

    def test_disable_builtin_hooks(self):
        td = typeddict_from_dict('Row', {'tags': ['a']}, include_builtin_type_hooks=False)
        self.assertIs(td.__annotations__['tags'], list)
        td = typeddict_from_dict('Row', {'tags': []}, include_builtin_type_hooks=False,
                                 type_hooks={list: lambda t, v: tuple[str, ...]})
        self.assertEqual(round_trip(td).__annotations__, {'tags': tuple[str, ...]})

    def test_container_types_survive_a_round_trip(self):
        data = {'items': [1, 'a', 2], 'set': {1, 'a'}, 'frozen': frozenset({1}),
                'empty': [], 'pair': ('a', 1), 'zero': (), 'nothing': None}
        expected = {'items': list[int | str], 'set': set[int | str], 'frozen': frozenset[int],
                    'empty': list[Any], 'pair': tuple[str, int], 'zero': tuple[()], 'nothing': type(None)}
        td = typeddict_from_dict('Row', data)
        self.assertEqual(get_type_hints(td), expected)
        self.assertEqual(get_type_hints(round_trip(td)), expected)

    def test_nested_container_members_have_explicit_arguments(self):
        td = typeddict_from_dict('Row', {'rows': [{'field': 1}], 'batch': ([], {})})
        hints = round_trip(td).__annotations__
        self.assertEqual(get_args(hints['rows'])[0].__annotations__, {'field': int})
        self.assertEqual(hints['batch'], tuple[list[Any], dict[Any, Any]])

    def test_bad_input_and_cycles(self):
        with self.assertRaisesRegex(TypeError, 'root'):
            typeddict_from_dict('Row', [])
        with self.assertRaisesRegex(TypeError, 'string key'):
            typeddict_from_dict('Row', {'nested': {1: 'bad'}})
        cycle = {}
        cycle['self'] = cycle
        with self.assertRaisesRegex(ValueError, 'self'):
            typeddict_from_dict('Row', cycle)


class DeclarationTests(unittest.TestCase):
    def test_class_defined_schema_including_inheritance_and_shared_dependencies(self):
        source = declaration_module_from_typeddict(Record)
        self.assertEqual(source.count('class Address('), 1)
        saved = round_trip(Record)
        hints = get_type_hints(saved, include_extras=True)
        self.assertEqual(hints['address'].__annotations__, {'city': str})
        self.assertIs(hints['address'], get_args(hints['previous'])[0])
        self.assertEqual(hints['tags'], NotRequired[list[str]])
        self.assertEqual(hints['code'], Required[Literal['A', 'B']])
        self.assertEqual(hints['created'], date | None)
        self.assertEqual(saved.__required_keys__, Record.__required_keys__)
        self.assertEqual(saved.__optional_keys__, Record.__optional_keys__)

    def test_legacy_mapping_from_older_factory(self):
        legacy = TypedDict('Legacy', {'fields': {'hello': str, 'enabled': True}})
        self.assertEqual(round_trip(legacy).__annotations__, {'hello': str, 'enabled': Literal[True]})

    def test_empty_and_non_identifier_keys(self):
        data = {'': {}, '1': 5, 'class': True, 'two words': 1, '__secret': None, 'hy-phen': 'x', 'K': 2}
        td = typeddict_from_dict('Root', data, total=False)
        saved = round_trip(td)
        self.assertEqual(saved.__optional_keys__, set(data))
        self.assertEqual(saved.__annotations__[''].__annotations__, {})
        self.assertEqual(round_trip(typeddict_from_dict('Empty', {})).__annotations__, {})

    def test_name_collisions_preserve_each_definition(self):
        td = typeddict_from_dict('Root', {'a-b': {'x': 1}, 'a_b': {'y': 's'}, 'literal': {}, 'root': {},
                                         'value': 1}, literals_where_possible=True)
        hints = round_trip(td).__annotations__
        self.assertEqual(hints['a-b'].__annotations__, {'x': Literal[1]})
        self.assertEqual(hints['a_b'].__annotations__, {'y': Literal['s']})
        self.assertEqual(hints['value'], Literal[1])
        self.assertNotEqual(hints['root'].__name__, 'Root')

    def test_wrapped_literals_preserve_exact_values(self):
        value = ("żółć 'q'  \\ \tline\n" * 15) + '  '
        data = {'message': value, 'raw': b'\x00', 'b': False, 'n': 0}
        td = typeddict_from_dict('Text', data, literals_where_possible=True)
        source = declaration_module_from_typeddict(td, str_literals_break_at=79)
        unwrapped = declaration_module_from_typeddict(td, str_literals_break_at=None)
        self.assertGreater(len(source.splitlines()), len(unwrapped.splitlines()))
        self.assertEqual(round_trip(td, str_literals_break_at=79).__annotations__, td.__annotations__)

    def test_annotations_from_type_hooks_round_trip(self):
        hint = Annotated[Callable[[date, int], list[date] | None], 'schedule']
        td = typeddict_from_dict('Row', {'fn': 1}, type_hooks={int: lambda t, v: hint})
        self.assertEqual(get_type_hints(round_trip(td), include_extras=True), {'fn': hint})

    def test_numeric_fields_with_a_plain_class_base(self):
        td = typeddict_from_dict('Row', {'42': 0})
        self.assertEqual(round_trip(td, inherit_cls=None).__annotations__, {'_42': int})

    def test_invalid_class_name_and_recursive_schema(self):
        with self.assertRaisesRegex(ValueError, 'not valid'):
            declaration_module_from_typeddict(typeddict_from_dict('not valid', {}))
        node = TypedDict('Node', {'child': 'Node'})
        with patch.dict(globals(), Node=node):
            with self.assertRaisesRegex(ValueError, 'Recursive TypedDict'):
                declaration_module_from_typeddict(node)

    def test_format_and_base_options(self):
        td = typeddict_from_dict('Row', {'count': 1})
        self.assertTrue(declaration_module_from_typeddict(td).startswith(f'# typeshi ({__version__})\n'))
        for base, bases in [(None, (object,)), (dict, (dict,))]:
            with self.subTest(base=base):
                opts = dict(inherit_cls=base, typeshi_header=False, end_with_newline=False, newline='\r\n')
                source = declaration_module_from_typeddict(td, **opts)
                self.assertNotIn('\n', source.replace('\r\n', ''))
                self.assertFalse(source.endswith('\n'))
                self.assertFalse(source.startswith('#'))
                self.assertEqual(round_trip(td, **opts).__bases__, bases)
        with self.assertRaises(ValueError):
            declaration_module_from_typeddict(td, str_literals_break_at=78)


class JsonFileTests(unittest.TestCase):
    def test_round_trip_paths_unicode_and_literal_option(self):
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory, 'data.json')
            out = Path(directory, 'schema.py')
            src.write_text(json.dumps({'fields': 'café', 'active': True}, ensure_ascii=False), encoding='utf-8')
            for as_path, literals in [(os.fsencode, False), (str, True), (Path, True)]:
                with self.subTest(as_path=as_path):
                    save_declaration_module_from_json('Data', as_path(src), as_path(out),
                                                      literals_where_possible=literals)
                    expected = {'fields': Literal['café'], 'active': Literal[True]} if literals else {'fields': str, 'active': bool}
                    self.assertEqual(import_declaration(out).Data.__annotations__, expected)

    def test_warning_and_output_preservation_on_generation_error(self):
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory, 'data.json')
            out = Path(directory, 'out.txt')
            src.write_text('{}')
            with self.assertWarnsRegex(UserWarning, 'out.txt'):
                save_declaration_module_from_json('Data', src, out)
            before = out.read_bytes()
            with warnings.catch_warnings():
                warnings.simplefilter('error')
                with self.assertRaises(ValueError):
                    save_declaration_module_from_json('Data', src, out, str_literals_break_at=10,
                                                      no_nonpy_declaration_path_warning=True)
            self.assertEqual(out.read_bytes(), before)
