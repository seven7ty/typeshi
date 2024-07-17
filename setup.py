#!/usr/bin/env python
import setuptools
import re

with open('README.md') as readme:
    long_description = readme.read()

with open('typeshi/version.py') as f:
    version = '.'.join(re.search(r'^version_info\s*=\s*VersionInfo\(major=(\d),\s*minor=(\d),\s*micro=(\d)(?:,\s*releaselevel\s*=\s*\'\w+\',\s*serial\s*=\s*\d)*\)', f.read(), re.MULTILINE).groups())

if not version:
    raise RuntimeError('version is not set')


setuptools.setup(
    name='typeshi',
    version=version,
    description='Easy-to-use TypedDict generation utilities',
    long_description=long_description,
    long_description_content_type='text/markdown',
    include_package_data=True,
    license='MIT',
    author='Paul Przybyszewski',
    author_email='paul@przybyszew.ski',
    url='https://github.com/seven7ty/typeshi',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License'
    ],
    python_requires='>=3.11',
)
