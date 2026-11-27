# coding: utf-8

import os
import json
import typing
import warnings
from pathlib import Path
from stat import S_ISREG
from tempfile import TemporaryDirectory
from typeshi.cls import typeddict_from_dict, typeddict_from_records
from typeshi.str_repr import declaration_module_from_typeddict

__all__: tuple = ('save_declaration_module_from_json',)


def _declaration_from_json(toplevel_cls_name, json_path, *, literals_where_possible=True,
                           inherit_cls=typing.TypedDict, typeshi_header=True, str_literals_break_at=119):
    with open(json_path, 'rb') as json_fp:
        data = json.load(json_fp)
    factory = typeddict_from_records if isinstance(data, list) else typeddict_from_dict
    schema = factory(toplevel_cls_name, data, literals_where_possible=literals_where_possible)
    return declaration_module_from_typeddict(schema, inherit_cls=inherit_cls, typeshi_header=typeshi_header,
                                             str_literals_break_at=str_literals_break_at)


def _write_declaration(path, source):
    target = Path(os.fsdecode(path)).resolve()
    try:
        mode = target.stat().st_mode
    except FileNotFoundError:
        mode = None
    if mode is not None and not S_ISREG(mode):
        raise ValueError(f'Expected a regular output file: {path}')
    # Stage on the same filesystem so readers always see a complete declaration.
    with TemporaryDirectory(dir=target.parent) as directory:
        staged = Path(directory, 'declaration')
        staged.write_bytes(source.encode('utf-8'))
        if mode is not None:
            staged.chmod(mode & 0o777)
        os.replace(staged, target)


def save_declaration_module_from_json(toplevel_cls_name: str, json_path: str | bytes | os.PathLike,
                                      declaration_path: str | bytes | os.PathLike, *,
                                      literals_where_possible: bool = True,
                                      no_nonpy_declaration_path_warning: bool = False,
                                      inherit_cls: type | None = typing.TypedDict,
                                      typeshi_header: bool = True,
                                      str_literals_break_at: int | None = 119) -> None:
    """
    Generate and save a declaration from a JSON object or a nonempty array of records.
    For an array, toplevel_cls_name names the type of an individual record.

    :param toplevel_cls_name: the classname to use for the top-level class in the declaration
    :param json_path: the path to the json file which will be used for generation
    :param declaration_path: the path at which to save the generated declaration.
        Should end with .py, this function does not create intermediary subdirectories
    :param literals_where_possible: a shorthand for passing LITERAL_CONVERSION_TYPE_HOOKS into type_hooks;
        converts applicable types into their typing.Literal counterparts (<str "dog"> becomes Literal['dog'])
    :param inherit_cls: the class all generated defs should use, defaults to TypedDict, passed down to declaration_module_from_typeddict
    :param typeshi_header: whether to include the typeshi version header in the declaration file contents
    :param no_nonpy_declaration_path_warning: whether to suppress the builtin warning about writing to a non-Python file
    :param str_literals_break_at: the line length at which typing.Literal strings will be broken into multiple lines.
        This accounts for words and doesn't split them, hence the actual line breaks will rarely occur right at the
        specified position. Throws a ValueError for values below the PEP8 value of 79.
    """
    if not no_nonpy_declaration_path_warning and not os.fsdecode(declaration_path).endswith('.py'):
        warnings.warn(f'The supplied declaration_path "{declaration_path}" is not a Python file', stacklevel=2)
    source = _declaration_from_json(toplevel_cls_name, json_path, literals_where_possible=literals_where_possible,
                                    inherit_cls=inherit_cls, typeshi_header=typeshi_header,
                                    str_literals_break_at=str_literals_break_at)
    _write_declaration(declaration_path, source)
