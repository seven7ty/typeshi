# coding: utf-8

import keyword
import re
import typing
import unicodedata
from collections.abc import Iterable, Mapping
from frozendict import frozendict
from typeshi.util import to_pascal_case, T

__all__: tuple = ('typeddict_from_dict', 'typeddict_from_records', 'BUILTIN_TYPE_SUBSCRIPT_HOOKS', 'LITERAL_CONVERSION_TYPE_HOOKS')


_CONTAINER_MEMBER_HINTS = {
    dict: dict[typing.Any, typing.Any],
    list: list[typing.Any],
    set: set[typing.Any],
    frozenset: frozenset[typing.Any],
    tuple: tuple[typing.Any, ...],
}


def _sequence_or_set_hook(t: type, value):
    members = tuple(dict.fromkeys(map(type, value)))
    if isinstance(value, (set, frozenset)):
        members = sorted(members, key=lambda member: (member.__module__, member.__qualname__))
    hints = tuple(_CONTAINER_MEMBER_HINTS.get(member, member) for member in members)
    return t[typing.Union[hints] if hints else typing.Any]


def _tuple_type_hook(t: type, value: tuple):
    return t[tuple(_CONTAINER_MEMBER_HINTS.get(member, member) for member in map(type, value))]


BUILTIN_TYPE_SUBSCRIPT_HOOKS = frozendict({
    list: _sequence_or_set_hook,
    set: _sequence_or_set_hook,
    frozenset: _sequence_or_set_hook,
    tuple: _tuple_type_hook,
})

LITERAL_CONVERSION_TYPE_HOOKS: frozendict[type, typing.Callable[[type[T], T], type[T]]] = frozendict({
    t: lambda _, value: typing.Literal[value] for t in (bool, str, int, bytes)})


def _nested_td_name_base_hook(p: tuple[str, ...], _) -> str:
    name = to_pascal_case(re.sub(r'[^\w]+', '_', '_'.join(p)))
    name = unicodedata.normalize('NFKC', name)
    if not name.isidentifier() or keyword.iskeyword(name):
        name = 'Field' + ''.join(c for c in name if ('A' + c).isidentifier())
    return name


def typeddict_from_dict(typeddict_name: str, original_dict: dict[str, typing.Any], *, total: bool = True,
                        nested_typeddict_cls_name_hook: typing.Callable[
                            [tuple[str, ...], typing.Any], str] = _nested_td_name_base_hook,
                        type_hooks: Mapping[type, typing.Callable[[type[T], T], type[T]]] = BUILTIN_TYPE_SUBSCRIPT_HOOKS,
                        literals_where_possible: bool = False,
                        include_builtin_type_hooks: bool = True) -> type:
    """
    Generate a TypedDict declaration blueprinted with the types present in the given dict,
    using a recursive method for nested subdicts.

    :param typeddict_name: the classname to use for the top-level TypedDict
    :param original_dict: the dictionary to use as the blueprint for the TypedDict
    :param total: whether total=total should be passed down to every generated TypedDict
    :param nested_typeddict_cls_name_hook: an optional function to generate the desired classnames for nested TypedDicts
        that accepts a tuple-based representation of the dictionary path of the given nested TypedDict
        and the nested source dictionary for which the name is to be generated
    :param type_hooks: a dict of hooks (callbacks) that are called when a type can be enriched (sequence values, etc.)
        where a simple T can be transformed into T[A, B, C, ...] or anything else
    :param literals_where_possible: a shorthand for passing LITERAL_CONVERSION_TYPE_HOOKS into type_hooks;
        converts applicable types into their typing.Literal counterparts (<str "dog"> becomes Literal['dog'])
    :param include_builtin_type_hooks: whether to include builtin type hooks (tuple, list, set, frozenset).
        Non-default (passed) implementations of hooks for these types take precedence
    :return: the TypedDict with type annotations that match the types present in original_dict
    """
    if not isinstance(original_dict, dict):
        raise TypeError('Expected a dictionary at the root')

    return typeddict_from_records(
        typeddict_name, [original_dict], total=total, nested_typeddict_cls_name_hook=nested_typeddict_cls_name_hook,
        type_hooks=type_hooks, literals_where_possible=literals_where_possible,
        include_builtin_type_hooks=include_builtin_type_hooks,
    )


def _validate_record_graph(rows, infer_lists):
    # Check each input graph before pooling observations. A shared child appearing
    # in two rows (even as another root) is valid. Only an ancestor is a cycle.
    visited = set()
    active = set()

    def validate(value, path):
        is_record = isinstance(value, dict)
        if not is_record and not (infer_lists and type(value) is list):
            return
        identity = id(value)
        if identity in active:
            raise ValueError(f'Cyclic container at {path!r}')
        if identity in visited:
            return
        active.add(identity)
        children = value.items() if is_record else enumerate(value)
        for key, child in children:
            if is_record and not isinstance(key, str):
                raise TypeError(f'Expected a string key at {path!r}, got {key!r}')
            validate(child, (*path, key))
        active.remove(identity)
        visited.add(identity)

    for row in rows:
        validate(row, ())


def _merge_hints(hints):
    if not hints:
        return typing.Any
    if len(hints) == 1:
        return hints[0]
    if all(typing.get_origin(hint) is typing.Literal for hint in hints):
        return typing.Literal[tuple(arg for hint in hints for arg in typing.get_args(hint))]
    return typing.Union[tuple(hints)]


def typeddict_from_records(
    typeddict_name: str, records: Iterable[dict[str, typing.Any]], *, total: bool = True,
    nested_typeddict_cls_name_hook: typing.Callable[[tuple[str, ...], dict], str] = _nested_td_name_base_hook,
    type_hooks: Mapping[type, typing.Callable[[type[T], T], type[T]]] = BUILTIN_TYPE_SUBSCRIPT_HOOKS,
    literals_where_possible: bool = False, include_builtin_type_hooks: bool = True,
) -> type:
    """Infer one TypedDict from a nonempty iterable of dictionaries in first-seen field order.

    Missing keys become NotRequired. An explicit None contributes to the value type.
    Dictionary observations at a field merge recursively. List observations pool their
    elements, so empty lists contribute no evidence when other lists contain values.
    The naming hook receives the first dictionary at each path. An 'item' path segment
    denotes one level of list nesting. Other options match typeddict_from_dict.
    """
    if isinstance(records, (Mapping, str, bytes)):
        raise TypeError('Expected an iterable of records')
    rows = list(records)
    if not rows:
        raise ValueError('Expected at least one record')
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TypeError(f'Expected a dictionary at record {index}')

    hooks = dict(LITERAL_CONVERSION_TYPE_HOOKS) if literals_where_possible else {}
    if include_builtin_type_hooks:
        hooks.update(BUILTIN_TYPE_SUBSCRIPT_HOOKS)
    if type_hooks is not BUILTIN_TYPE_SUBSCRIPT_HOOKS:
        hooks.update(type_hooks)
    infer_lists = hooks.get(list) is _sequence_or_set_hook
    names = {typeddict_name}

    _validate_record_graph(rows, infer_lists)

    def child_name(path, sample):
        base = nested_typeddict_cls_name_hook(path, sample)
        name = base
        suffix = 2
        while name in names:
            name = f'{base}{suffix}'
            suffix += 1
        names.add(name)
        return name

    def infer(values, path, *, list_items=False):
        # Group structured values before recursing so one path gets one record type.
        groups = {}
        for value in values:
            kind = dict if isinstance(value, dict) else type(value)
            groups.setdefault(kind, []).append(value)
        hints = []
        for kind, samples in groups.items():
            if kind is dict:
                hints.append(build(child_name(path, samples[0]), samples, path))
            elif kind is list and infer_lists:
                items = (item for sample in samples for item in sample)
                hints.append(list[infer(items, (*path, 'item'), list_items=True)])
            elif list_items:
                # Scalar list elements historically use their types, even in literal mode.
                hints.append(_CONTAINER_MEMBER_HINTS.get(kind, kind))
            elif kind in hooks:
                hints.extend(hooks[kind](kind, value) for value in samples)
            else:
                hints.append(kind)
        return _merge_hints(hints)

    def build(name, samples, path):
        columns = {}
        for sample in samples:
            for key, value in sample.items():
                columns.setdefault(key, []).append(value)
        fields = {}
        for key, values in columns.items():
            hint = infer(values, (*path, key))
            if total and len(values) < len(samples):
                hint = typing.NotRequired[hint]
            fields[key] = hint
        return typing.TypedDict(name, fields, total=total)

    return build(typeddict_name, rows, ())
