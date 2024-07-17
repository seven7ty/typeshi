# coding: utf-8

"""
typeshi - TypedDict generation utilities
~~~~~~~~~~~~~~~~~~
:copyright: (c) 2024 Paul Przybyszewski
:license: MIT, see LICENSE for more details.
"""

from .cls import *
from .str_repr import *

from collections import namedtuple

VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')

version_info = VersionInfo(major=1, minor=0, micro=0, releaselevel='final', serial=0)

__version__ = f'{version_info.major}.{version_info.minor}.{version_info.micro}'
__title__ = 'typeshi'
__license__ = 'MIT'
__author__ = 'Paul Przybyszewski'
__email__ = 'paul@przybyszew.ski'
__uri__ = "https://github.com/seven7ty/typeshi"
__copyright__ = 'Copyright 2024 %s' % __author__

__path__ = __import__('pkgutil').extend_path(__path__, __name__)
