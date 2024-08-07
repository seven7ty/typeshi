# coding: utf-8

from collections import namedtuple

VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')
version_info = VersionInfo(major=2, minor=0, micro=1, releaselevel='final', serial=0)
__version__ = f'{version_info.major}.{version_info.minor}.{version_info.micro}'
