import unittest

from typeshi.util import dict_full_path, get_all_dict_paths, get_nested_key, is_builtin, remove_all_but_first, to_pascal_case


class UtilityTests(unittest.TestCase):
    def test_lookup_paths_and_indices(self):
        data = {'x': {'items': [[3]], 'items[1]': 'literal key'}, 'other': {'items': 2}}
        self.assertEqual(get_all_dict_paths(data), [('x', 'items'), ('x', 'items[1]'), ('other', 'items')])
        self.assertEqual(get_nested_key(data, 'x/items[0][0]', sep='/'), 3)
        self.assertEqual(get_nested_key(data, ('x', 'items[1]')), 'literal key')
        self.assertEqual(dict_full_path(data, 'items', 2), ('other', 'items'))
        self.assertIsNone(dict_full_path(data, 'missing'))

    def test_deduplicate_in_place(self):
        items = [0, 1, 1, 2, 1, 1, 3]
        self.assertIs(remove_all_but_first(items, 1), items)
        self.assertEqual(items, [0, 1, 2, 3])

    def test_naming_and_builtin_predicate(self):
        self.assertEqual(to_pascal_case('foo_bar'), 'FooBar')
        self.assertTrue(is_builtin(str))
        self.assertFalse(is_builtin(UtilityTests))
