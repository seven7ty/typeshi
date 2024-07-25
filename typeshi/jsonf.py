# coding: utf-8

import os
import json
import typing
import warnings
from typeshi.cls import typeddict_from_dict
from typeshi.str_repr import declaration_module_from_typeddict

__all__: tuple = ('save_declaration_module_from_json',)


def save_declaration_module_from_json(toplevel_cls_name: str, json_path: str | bytes | os.PathLike,
                                      declaration_path: str | bytes | os.PathLike, *,
                                      literals_where_possible: bool = True,
                                      no_nonpy_declaration_path_warning: bool = False,
                                      inherit_cls: type | None = typing.TypedDict,
                                      typeshi_header: bool = True,
                                      str_literals_break_at: int | None = 119) -> None:
    """
    Generate and save a declaration file based on the data contained in a JSON file

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
    hooks: dict = {}
    if literals_where_possible:
        for t in (int, str, bool):
            hooks[t] = lambda _, v: typing.Literal[v]
    if not declaration_path.endswith('.py') and not no_nonpy_declaration_path_warning:
        warnings.warn(f'The supplied declaration_path "{declaration_path}" is not a Python file')
    with open(json_path) as json_fp:
        td: typing._TypedDictMeta = typeddict_from_dict(toplevel_cls_name, json.load(json_fp), type_hooks=hooks)
    with open(declaration_path, 'w+') as py_fp:
        py_fp.write(declaration_module_from_typeddict(td, inherit_cls=inherit_cls, typeshi_header=typeshi_header,
                                                      str_literals_break_at=str_literals_break_at))
