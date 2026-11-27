#!/usr/bin/env python
import setuptools
from runpy import run_path

with open('README_DIST.md', encoding='utf-8') as readme:
    long_description = readme.read()

version = run_path('typeshi/version.py')['__version__']


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
    entry_points={'console_scripts': ['typeshi=typeshi.cli:main']},
    classifiers=[
        'Programming Language :: Python :: 3'
    ],
    python_requires='>=3.11',
    install_requires=[
        'frozendict'
    ]
)
