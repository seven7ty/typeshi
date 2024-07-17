# `typeshi` - a dead-simple TypedDict utility
Sometimes when working with Python typing we come across a situation when we need to quickly get a TypedDict object from an existing dict, and then maybe even make it into a self-contained declaration file -- `typeshi` does both of these things.

## Installation
```
$ pip install typeshi
```

## A quick example
`typeshi` exposes two functions, `typeddict_from_dict` and `declaration_module_from_typeddict`. `typeddict_from_dict` is used to get a TypedDict from a dict instance at runtime, whereas `declaration_module_from_typeddict` generates the contents of a declaration module from a TypedDict.
The most common usage of `typeshi` would be something like this:
```py
# Let's say I have some JSON file that I load into my app at runtime,
# maybe it contains something like a locale or a config file...
# Let's say it's a locale for the sake of this example
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
# since in this example I'm thinking of a locale, that's what I'll name my TypedDict
td = typeshi.typeddict_from_dict(typeddict_name='Locale', original_dict=my_dict)

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
import typing


class GreetingsEvening(typing.TypedDict):
    polite: str
    ...

class Greetings(typing.TypedDict):
    evening: GreetingsEvening
    ...

class Locale(typing.TypedDict):
    greetings: Greetings
    ...
```

```py
# Okay! With that done, I can now import my TypedDict and use it to type hint my locale
from generated.locale_declaration import Locale

my_dict: Locale

print(my_dict['greetings']['evening']['polite'])  # Intellisense tells me this is a string!
```

Now, the locale example is obviously limiting, but the heart of `typeshi`, that being `typeddict_from_dict`, becomes very useful very quickly.
It supports custom hooks for types and the naming of nested TypedDict classes, making it very easy to use and flexible -- everything is documented within docstrings.
