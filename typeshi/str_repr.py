# coding: utf-8

import typing
from types import NoneType
from typeshi.version import __version__
from typeshi.util import is_builtin, remove_all_but_first, resolve_main_module, T

__all__: tuple = ('declaration_module_from_typeddict',)
__PEP8_INDENT__: str = '    '
__MAIN_MODULE__: str = resolve_main_module()
__TYPESHI_HEADER__: str = f'# typeshi ({__version__})'


def _prep_type(t: T) -> str:
    if t is NoneType:
        return 'None'
    return t.__name__ if hasattr(t, '__name__') else t.__class__.__name__ + (
        f'[{", ".join(map(lambda _t: _t.__name__, t.__args__))}]' if hasattr(t, '__args__') and t.__args__ else '')


def get_type_module(t: T) -> str:
    return t.__module__ if not t.__module__ == '__main__' else __MAIN_MODULE__


def declaration_module_from_typeddict(typeddict: typing._TypedDictMeta, *,
                                      newline: str = '\n', end_with_newline: bool = True,
                                      typeshi_header: bool = True, inherit_cls: type | None = typing.TypedDict) -> str:
    """
    Get the class definitions of a TypedDict in the form of the content of a self-contained, ready-to-import module.
    This function resolves imports and handles class ordering, returning a ready-to-go, complete TypedDict declaration.

    :param typeddict: the TypedDict for which to generate the definitions
    :param newline: what character to use for the newline
    :param end_with_newline: whether to end the "file" with a newline
    :param typeshi_header: whether to include the typeshi version header in the declaration file contents
    :param inherit_cls: the class all generated defs should use, defaults to TypedDict
    :return: the generated definition file contents
    """
    cls_definitions: list[str] = []
    from_imports: dict[str, list[str]] = {get_type_module(inherit_cls): [inherit_cls.__name__]} if inherit_cls else {}
    inherit_cls_suffix: str = f'({inherit_cls.__name__})' if inherit_cls else ''
    header: str = __TYPESHI_HEADER__ + '\n\n' if typeshi_header else ''

    def _nested_class_declarations_from_typeddict(td: typing._TypedDictMeta):
        nonlocal cls_definitions

        defn: str = f'class {td.__name__}{inherit_cls_suffix}:'
        for k, v in td.__annotations__['fields'].items():
            defn += f'\n{__PEP8_INDENT__}{k if not k.isnumeric() else f"_{k}"}: {_prep_type(v)}'
            if not is_builtin(v) and v.__module__ != 'typeshi.cls':
                module: str = v.__module__ if not v.__module__ == '__main__' else __MAIN_MODULE__
                if module in from_imports:
                    from_imports[module].append(_prep_type(v))
                else:
                    from_imports[module] = [_prep_type(v)]
            if isinstance(v, typing._TypedDictMeta):
                _nested_class_declarations_from_typeddict(v)
        cls_definitions.append(defn)

    _nested_class_declarations_from_typeddict(typeddict)

    for cls_d in cls_definitions:
        remove_all_but_first(cls_definitions, cls_d)

    for fik, fiv in from_imports.items():
        header += f'from {fik} import ' + ', '.join(fiv) + '\n'

    return (header + (newline * 2 if from_imports else '')
            + f'{newline * 3}'.join(cls_definitions) + (newline if end_with_newline else ''))
