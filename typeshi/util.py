# coding: utf-8

import os
import sys
import typing


def to_pascal_case(str_: str) -> str:
    """
    Convert a snake_case string to PascalCase

    :param str_: The string to convert
    :return: The converted string
    """
    return ''.join(word.capitalize() for word in str_.split('_'))


def get_all_dict_paths(d: dict, *, __path: tuple[str, ...] | None = None) -> list[tuple[str, ...]]:
    # https://github.com/statch/gitbot/blob/main/lib/utils/dict_utils.py#L87-L101
    """
    Get all paths in a dictionary

    :param d: The dictionary to get the paths from
    :return: A list of paths
    """
    __path: tuple = () if __path is None else __path
    paths: list = []
    for k, v in d.items():
        if isinstance(v, dict):
            paths.extend(get_all_dict_paths(v, __path=__path + (k,)))
        else:
            paths.append(__path + (k,))
    return paths


def get_nested_key(dict_: dict, key: typing.Iterable[str] | str, sep: str = ' ') -> typing.Any:
    # https://github.com/statch/gitbot/blob/main/lib/utils/dict_utils.py#L65-L85
    """
    Get a nested dictionary key

    :param dict_: The dictionary to get the key from
    :param key: The key to get
    :param sep: The separator to use if key is a string
    :return: The value associated with the key
    """
    if isinstance(key, str):
        key = key.split(sep=sep)

    for k in key:
        if k.endswith(']'):  # list-like indexes
            index_start = k.index('[')
            index = int(k[index_start + 1:-1])
            dict_ = dict_[index]
        else:
            try:
                dict_ = dict_.get(k)
            except AttributeError:
                return dict_

    return dict_


def dict_full_path(dict_: dict,
                   key: str,
                   value: typing.Any = None) -> tuple[str, ...] | None:
    """
    Get the full path of a dictionary key in the form of a tuple.
    The value is an optional parameter that can be used to determine which key's path to return if many are present.

    :param dict_: The dictionary to which the key belongs
    :param key: The key to get the full path to
    :param value: The optional value for determining if a key is the right one
    :return: None if key not in dict_ or dict_[key] != value if value is not None else the full path to the key
    """
    def _recursive(__prev: tuple = ()) -> tuple[str, ...] | None:
        reduced: dict = get_nested_key(dict_, __prev)
        for k, v in reduced.items():
            if k == key and (value is None or (value is not None and v == value)):
                return *__prev, key
            if isinstance(v, dict):
                if ret := _recursive((*__prev, k)):
                    return ret

    return _recursive()


def is_builtin(obj: object) -> bool:
    """
    Check whether object belongs to the builtins module

    :param obj: object to check
    :return: whether obj is a builtin
    """
    return obj.__module__ == 'builtins'


def remove_all_but_first(list_: list[typing.Any], v: typing.Any) -> list[typing.Any]:
    """
    Remove all occurrences of a value in a list except the first one (inplace)

    :param list_: the list to remove duplicate values from
    :param v: the value of which only the first instance should be kept
    :return: the deduplicated list (although it is done inplace as well)
    """
    first_i: int = list_.index(v)
    to_remove: list[typing.Any] = []

    for i, item in enumerate(list_):
        if item == v and i != first_i:
            to_remove.append(i)

    for i in to_remove:
        del list_[i]

    return list_


def resolve_main_module() -> str | None:
    """
    Get the actual import path of the __main__ module

    :return: the resolved main module
    """
    main_script_path = sys.argv[0]

    if not main_script_path:
        return None  # if running interactively just return None

    # Convert file path to module path
    module_path = os.path.relpath(main_script_path, os.getcwd()).replace(os.sep, '.')
    if module_path.endswith('.py'):
        module_path = module_path[:-3]

    return module_path
