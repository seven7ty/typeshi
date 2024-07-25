<h1 align="center"><code>typeshi</code> - a dead-simple TypedDict utility</h1>
<p align="center">
    <a href="https://pypi.org/project/typeshi/"><img src="https://img.shields.io/pypi/v/typeshi?color=3776AB&logo=python&style=for-the-badge"/></a>
    <a href="https://pypi.org/project/typeshi/"><img src="https://img.shields.io/pypi/dm/typeshi?color=3776AB&logo=python&style=for-the-badge"/></a>
</p>


_________________
Sometimes when working with Python typing we come across a situation when we need to quickly get a TypedDict object from an existing dict, and then maybe even make it into a self-contained declaration file -- `typeshi` does both of these things while exposing helpful function interfaces and utilities.
You can get started right away by looking at the docstrings of the exposed functions listed below in your favorite code editor, or get a general feel for `typeshi` first with the examples that follow.

### Documented functions of `typeshi`
- **`typeddict_from_dict`**
- **`declaration_module_from_typeddict`**
- `save_declaration_module_from_json`

## Installation
```
$ pip install typeshi
```

## A quick example
`typeshi` exposes two main functions, `typeddict_from_dict` and `declaration_module_from_typeddict`. `typeddict_from_dict` is used to get a TypedDict from a dict instance at runtime, whereas `declaration_module_from_typeddict` generates the contents of a declaration module from a TypedDict.
The most common usage of `typeshi` would be something like this:
```py
# Let's say I have some JSON file that I load into my app at runtime,
# maybe it contains something like a locale or a config file...
# For the sake of this example let this be some sort of locale
with open(MY_JSON) as fp:
    my_dict = json.load(fp)

print(my_dict['greetings']['evening']['polite'])
# ^ I can *guess* that this is a string (and that it exists at all),
# but I'm lacking my Intellisense to be sure, let's change that
```

```py
# I kind of wish I could develop easier with the help of type hints of my locale,
# this is where typeshi comes in:
import typeshi

# first, I'll generate my TypedDict
# since in this example I'm thinking of a locale, I'll name my TypedDict "Locale" as well as tell typeshi
# to convert applicable types into their typing.Literal counterparts, which will make my life easier while coding
td = typeshi.typeddict_from_dict(typeddict_name='Locale', original_dict=my_dict, literals_where_possible=True)

# Now my TypedDict is already generated, but it doesn't do much for me if it's just sitting in memory...
# I'll generate a declaration file so that I can import it and type hint my locale
declaration = typeshi.declaration_module_from_typeddict(td)
# okay, that's my declaration ready, now I'll just save it to a Python file of my choice...
with open('generated/locale_declaration.py', 'w+') as fp:
    fp.write(declaration)
```
```py
# a generated typeshi declaration file will look something like this:

# generated/locale_declaration.py
from typing import TypedDict, Literal


class GreetingsEvening(TypedDict):
    polite: Literal['Good evening!']
    ...

class Greetings(TypedDict):
    evening: GreetingsEvening
    ...

class Locale(TypedDict):
    greetings: Greetings
    ...
```

```py
# Okay! With that done, I can now import my TypedDict and use it to type hint my locale
from generated.locale_declaration import Locale

my_dict: Locale  # tell my editor that this is of my Locale type
my_dict['greetings']['evening']['polite']  # Literal['Good evening!']
```

Now, the locale example is obviously limiting, but the heart of `typeshi`, that being `typeddict_from_dict`, becomes very useful very quickly.
It supports custom hooks for types and the naming of nested TypedDict classes, making it very easy to use and flexible -- ***everything is documented within docstrings.***

It's worth noting the above example is significantly shortened by using the typeshi helper function `save_declaration_module_from_json` as follows:
```py
from typeshi import save_declaration_module_from_json

save_declaration_module_from_json(toplevel_cls_name='Locale', json_path='my_json.json',
                                  declaration_path='generated/locale_declaration.py')
```
