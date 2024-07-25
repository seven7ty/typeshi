# coding: utf-8

import typing
import textwrap
from types import NoneType
from typeshi.version import __version__
from typeshi.util import is_builtin, remove_all_but_first, resolve_main_module, T

__all__: tuple = ('declaration_module_from_typeddict',)
__PEP8_INDENT__: str = '    '
__MAIN_MODULE__: str = resolve_main_module()
__TYPESHI_HEADER__: str = f'# typeshi ({__version__})'


def _prep_type(t: T, expand_args: bool = True, *, literals_break_at: int | None = None,
               value_name: str | None = None) -> str:
    if t is NoneType:  # make this a literal since NoneType can only ever have the value of None, no sense otherwise
        return 'None'
    elif isinstance(t, typing._LiteralGenericAlias) and expand_args:
        content: str | bytes | int | bool = t.__args__[0]
        if isinstance(content, str) and literals_break_at and len(content) > literals_break_at - len(value_name) - 15:
            segments: list[str] = textwrap.wrap(str(t)[7:], width=literals_break_at - 2,
                                                initial_indent=' ' * (len(value_name) + 6),
                                                subsequent_indent=__PEP8_INDENT__ + ' ' * (len(value_name) + 11))
            segments[0]: str = segments[0].strip()  # since we use the hacky initial indent above, remove it
            return ' \\\n'.join(segments)
        return str(t)[7:]
    return t.__name__ if hasattr(t, '__name__') else t.__class__.__name__ + (
        f'[{", ".join(map(lambda _t: _t.__name__, t.__args__))}]' if (
                hasattr(t, '__args__') and t.__args__ and expand_args) else '')


def get_type_module(t: T) -> str:
    return t.__module__ if not t.__module__ == '__main__' else __MAIN_MODULE__


def declaration_module_from_typeddict(typeddict: typing._TypedDictMeta, *,
                                      newline: str = '\n', end_with_newline: bool = True,
                                      typeshi_header: bool = True, inherit_cls: type | None = typing.TypedDict,
                                      str_literals_break_at: int | None = 119) -> str:
    """
    Get the class definitions of a TypedDict in the form of the content of a self-contained, ready-to-import module.
    This function resolves imports and handles class ordering, returning a ready-to-go, complete TypedDict declaration.

    :param typeddict: the TypedDict for which to generate the definitions
    :param newline: what character to use for the newline
    :param end_with_newline: whether to end the "file" with a newline
    :param typeshi_header: whether to include the typeshi version header in the declaration file contents
    :param inherit_cls: the class all generated defs should use, defaults to TypedDict
    :param str_literals_break_at: the line length at which typing.Literal strings will be broken into multiple lines
        This accounts for words, hence the actual line breaks will rarely occur right at the specified position.
        Throws a ValueError for values below the PEP8 value of 79.
    :return: the generated definition file contents
    """
    if str_literals_break_at and str_literals_break_at < 79:
        raise ValueError('Expected sane linebreak point for string literals (>=79)')

    cls_definitions: list[str] = []
    from_imports: dict[str, list[str]] = {get_type_module(inherit_cls): [inherit_cls.__name__]} if inherit_cls else {}

    def _nested_class_declarations_from_typeddict(td: typing._TypedDictMeta):
        if (inherit_cls and inherit_cls is typing.TypedDict) and not td.__total__:
            defn: str = f'class {td.__name__}(TypedDict, total=False):'
        else:
            defn: str = f'class {td.__name__}' + (f'({inherit_cls.__name__}):' if inherit_cls else ':')
        for k, v in td.__annotations__['fields'].items():
            defn += (f'\n{__PEP8_INDENT__}{k if not k.isnumeric() else f"_{k}"}: '
                     f'{_prep_type(v, literals_break_at=str_literals_break_at, value_name=k)}')
            if not is_builtin(v) and v.__module__ != 'typeshi.cls':
                module: str = v.__module__ if not v.__module__ == '__main__' else __MAIN_MODULE__
                prepped_import_t: str = _prep_type(v, expand_args=False)
                if module in from_imports and prepped_import_t not in from_imports[module]:
                    from_imports[module].append(prepped_import_t)
                elif module not in from_imports:
                    from_imports[module] = [prepped_import_t]
            if isinstance(v, typing._TypedDictMeta):
                _nested_class_declarations_from_typeddict(v)
        cls_definitions.append(defn)

    _nested_class_declarations_from_typeddict(typeddict)

    for cls_d in cls_definitions:
        remove_all_but_first(cls_definitions, cls_d)

    header: str = __TYPESHI_HEADER__ + '\n\n' if typeshi_header else ''

    for fik, fiv in from_imports.items():
        header += f'from {fik} import ' + ', '.join(fiv) + '\n'

    return (header + (newline * 2 if from_imports else '')
            + f'{newline * 3}'.join(cls_definitions) + (newline if end_with_newline else ''))
