# coding: utf-8

import enum
import keyword
import textwrap
import types
import typing
import unicodedata
from typeshi.util import resolve_main_module
from typeshi.version import __version__

__all__ = ('declaration_module_from_typeddict',)
_TRANSPARENT_QUALIFIERS = (typing.Annotated,)
if hasattr(typing, 'ReadOnly'):
    _TRANSPARENT_QUALIFIERS += (typing.ReadOnly,)


def _identifier(name: str) -> bool:
    return (name != '__debug__' and name.isidentifier() and not keyword.iskeyword(name)
            and unicodedata.normalize('NFKC', name) == name)


def _literal_string(value: str, width: int | None, indent: str) -> str:
    if width is None or len(repr(value)) + len(indent) + 1 <= width:
        return repr(value)
    chunks = textwrap.wrap(value, width=max(1, width - len(indent) - 3),
                           expand_tabs=False, replace_whitespace=False, drop_whitespace=False,
                           break_long_words=False, break_on_hyphens=False)
    return ('\n' + indent).join(map(repr, chunks)) if chunks else repr(value)


def _ordered_schemas(typeddict):
    # Collect children first so every declaration can reference an existing name.
    schemas = {}
    names = set()
    visiting = set()

    def visit_annotation(annotation):
        if typing.is_typeddict(annotation):
            visit(annotation)
        else:
            for arg in typing.get_args(annotation):
                if isinstance(arg, list):  # Callable's argument list
                    for item in arg:
                        visit_annotation(item)
                else:
                    visit_annotation(arg)

    def visit(td):
        if td in schemas:
            return
        if td in visiting:
            raise ValueError(f'Recursive TypedDict {td.__name__!r} cannot be emitted')
        name = td.__name__
        if not _identifier(name) or name in names:
            raise ValueError(f'Invalid or duplicate TypedDict name {name!r}')
        names.add(name)
        visiting.add(td)
        annotations = td.__annotations__
        # Before 2.1 the factory produced a single field containing the mapping on 3.11/3.12.
        if annotations.keys() == {'fields'} and isinstance(annotations['fields'], dict):
            fields = {key: typing.Literal[hint] if isinstance(hint, bool) else hint
                      for key, hint in annotations['fields'].items()}
        else:
            fields = typing.get_type_hints(td, include_extras=True)
        for annotation in fields.values():
            visit_annotation(annotation)
        visiting.remove(td)
        schemas[td] = fields

    visit(typeddict)
    return schemas


def declaration_module_from_typeddict(typeddict: type, *,
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
    if str_literals_break_at is not None and str_literals_break_at < 79:
        raise ValueError('Expected sane linebreak point for string literals (>=79)')
    if not typing.is_typeddict(typeddict):
        raise TypeError('Expected a TypedDict')

    schemas = _ordered_schemas(typeddict)
    used_names = {schema.__name__ for schema in schemas}
    imports = {}
    references = {}

    def symbol(module, name):
        key = (module, name)
        if key in references:
            return references[key]
        alias = name
        while alias in used_names:
            alias += '_'
        used_names.add(alias)
        references[key] = alias
        if module != 'builtins' or alias != name:
            imports.setdefault(module, []).append(name if alias == name else f'{name} as {alias}')
        return alias

    def reference(obj):
        module = obj.__module__
        if module == '__main__':
            module = resolve_main_module()
        qualname = getattr(obj, '__qualname__', obj.__name__)
        if not module or not all(_identifier(part) for part in (*module.split('.'), *qualname.split('.'))):
            raise ValueError(f'Cannot import {obj!r} in a declaration module')
        root, dot, tail = qualname.partition('.')
        return symbol(module, root) + dot + tail

    def render(annotation, indent):
        if typing.is_typeddict(annotation):
            return annotation.__name__
        if annotation is types.NoneType or annotation is None:
            return 'None'
        if annotation is Ellipsis:
            return '...'
        origin = typing.get_origin(annotation)
        args = typing.get_args(annotation)
        if origin is typing.Literal:
            literal = symbol('typing', 'Literal')
            values = []
            for value in args:
                if isinstance(value, enum.Enum):
                    values.append(f'{reference(type(value))}.{value.name}')
                elif isinstance(value, str):
                    values.append(_literal_string(value, str_literals_break_at, indent + ' ' * (len(literal) + 1)))
                else:
                    values.append(repr(value))
            return f'{literal}[{", ".join(values)}]'
        if origin in (typing.Union, types.UnionType):
            return ' | '.join(render(arg, indent) for arg in args)
        if origin is typing.Annotated:
            metadata = ', '.join(map(repr, args[1:]))
            return f'{symbol("typing", "Annotated")}[{render(args[0], indent)}, {metadata}]'
        if origin is not None:
            # Preserve typing aliases (e.g. List and Callable) alongside PEP 585 generics.
            if annotation.__module__ == 'typing' and getattr(annotation, '__name__', None):
                base = symbol('typing', annotation.__name__)
            else:
                base = reference(origin)
            if not args:
                return base + ('[()]' if isinstance(annotation, types.GenericAlias) or annotation == typing.Tuple[()] else '')
            params = []
            for arg in args:
                if isinstance(arg, list):
                    params.append('[' + ', '.join(render(item, indent) for item in arg) + ']')
                else:
                    params.append(render(arg, indent))
            return f'{base}[{", ".join(params)}]'
        return reference(annotation)

    base = reference(inherit_cls) if inherit_cls is not None else None
    definitions = []
    for td, fields in schemas.items():
        if inherit_cls is not typing.TypedDict:
            # Plain classes historically expose numeric keys as attributes such as _1.
            fields_for_class = {f'_{k}' if k.isnumeric() else k: v for k, v in fields.items()}
            if len(fields_for_class) != len(fields) or any(not _identifier(k) for k in fields_for_class):
                raise ValueError('These keys cannot be represented as class attributes')
            fields = fields_for_class
        functional = inherit_cls is typing.TypedDict and any(
            not _identifier(key) or key.startswith('__') for key in fields
        )
        total = ', total=False' if inherit_cls is typing.TypedDict and not td.__total__ else ''
        if functional:
            lines = [f'{td.__name__} = {base}({td.__name__!r}, {{']
        else:
            bases = f'({base}{total})' if base else ''
            lines = [f'class {td.__name__}{bases}:']
        for key, annotation in fields.items():
            prefix = f'    {key!r}: ' if functional else f'    {key}: '
            hint = render(annotation, ' ' * len(prefix))
            # Flattened inherited annotations can disagree with the child's total setting.
            if inherit_cls is typing.TypedDict:
                qualifier = annotation
                while typing.get_origin(qualifier) in _TRANSPARENT_QUALIFIERS:
                    qualifier = typing.get_args(qualifier)[0]
                if typing.get_origin(qualifier) not in (typing.Required, typing.NotRequired):
                    if td.__total__ and key in td.__optional_keys__:
                        hint = f'{symbol("typing", "NotRequired")}[{hint}]'
                    elif not td.__total__ and key in td.__required_keys__:
                        hint = f'{symbol("typing", "Required")}[{hint}]'
            lines.append(prefix + hint + (',' if functional else ''))
        if functional:
            lines.append('}' + total + ')')
        elif not fields:
            lines.append('    pass')
        definitions.append('\n'.join(lines))

    sections = []
    if typeshi_header:
        sections.append(f'# typeshi ({__version__})\n\n')
    if imports:
        sections.append(''.join(f'from {module} import {", ".join(items)}\n' for module, items in imports.items()) + '\n\n')
    sections.append('\n\n\n'.join(definitions))
    if end_with_newline:
        sections.append('\n')
    return ''.join(sections).replace('\n', newline)
