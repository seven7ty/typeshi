# coding: utf-8

import typing
from frozendict import frozendict
from typeshi.util import to_pascal_case, dict_full_path

__all__: tuple = ('typeddict_from_dict', 'BUILTIN_TYPE_HOOKS')
T = typing.TypeVar('T')


def __generic_sequence_or_set_type_hook(t: type[T], v: T) -> type[T]:
    return t[*set(type(sv) for sv in v)]


def _list_type_hook(t: type[list], v: list) -> type[list]:
    return __generic_sequence_or_set_type_hook(t, v)


def _set_type_hook(t: type[set] | type[frozenset], v: set | frozenset) -> type[set] | type[frozenset]:
    return __generic_sequence_or_set_type_hook(t, v)


def _tuple_type_hook(t: type[tuple], v: tuple) -> type[tuple]:
    return t[*(type(sv) for sv in v)]


BUILTIN_TYPE_HOOKS: frozendict[type, typing.Callable[[type[T], T], type[T]]] = frozendict(
    {list: _list_type_hook, tuple: _tuple_type_hook, set: _set_type_hook, frozenset: _set_type_hook})


def _nested_td_name_base_hook(p: tuple[str, ...]) -> str:
    return to_pascal_case('_'.join(p))


def typeddict_from_dict(typeddict_name: str, original_dict: dict[str, ...], *, total: bool = True,
                        nested_typeddict_cls_name_hook: typing.Callable[
                            [tuple[str, ...]], str] = _nested_td_name_base_hook,
                        type_hooks: dict[type, typing.Callable[[type[T], T], type[T]]] = BUILTIN_TYPE_HOOKS,
                        include_builtin_type_hooks: bool = True) -> typing._TypedDictMeta:
    """
    Generate a TypedDict declaration blueprinted with the types present in the given dict,
    using a recursive method for nested subdicts.

    :param typeddict_name: the classname to use for the top-level TypedDict
    :param original_dict: the dictionary to use as the blueprint for the TypedDict
    :param total: whether total=total should be passed down to every generated TypedDict
    :param nested_typeddict_cls_name_hook: an optional function to generate the desired classnames for nested TypedDicts
        that accepts a tuple-based representation of the dictionary path of the given nested TypedDict
    :param type_hooks: a dict of hooks (callbacks) that are called when a type can be enriched (sequence values, etc.)
        where a simple T can be transformed into T[A, B, C, ...]
    :param include_builtin_type_hooks: whether to include builtin type hooks (tuple, list, set, frozenset).
        Non-default impls of hooks for these types take precedence
    :return: the TypedDict with type annotations that match the types present in original_dict
    """
    if include_builtin_type_hooks and type_hooks != BUILTIN_TYPE_HOOKS:
        for thk, thv in BUILTIN_TYPE_HOOKS.items():
            if thk not in type_hooks:
                type_hooks[thk] = thv
    elif not include_builtin_type_hooks and type_hooks == BUILTIN_TYPE_HOOKS:
        type_hooks: frozendict = frozendict()

    def _nested_typeddict_from_dict(td_cls_name: str, stage_dict: dict[str, ...]) -> type[typing.TypedDict]:
        td_kv_pairs: dict[str, typing.Any] = {}
        for k, v in stage_dict.items():
            if isinstance(v, dict):
                td_kv_pairs[k] = _nested_typeddict_from_dict(nested_typeddict_cls_name_hook(dict_full_path(original_dict, k, v)),v)
            else:
                v_type: typing.Any = type(v)
                td_kv_pairs[k] = type_hooks[v_type](v_type, v) if v_type in type_hooks else v_type
        return typing.TypedDict(td_cls_name, fields=td_kv_pairs, total=total)

    return _nested_typeddict_from_dict(typeddict_name, original_dict)
