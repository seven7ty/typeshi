# coding: utf-8

"""
typeshi - TypedDict generation utilities
~~~~~~~~~~~~~~~~~~
:copyright: (c) 2024 Paul Przybyszewski
:license: MIT, see LICENSE for more details.
"""

from .cls import *
from .str_repr import *
from .version import __version__, version_info

__title__ = 'typeshi'
__license__ = 'MIT'
__author__ = 'Paul Przybyszewski'
__email__ = 'paul@przybyszew.ski'
__uri__ = "https://github.com/seven7ty/typeshi"
__copyright__ = 'Copyright 2024 %s' % __author__

__path__ = __import__('pkgutil').extend_path(__path__, __name__)
