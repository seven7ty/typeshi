"""Generate a Python declaration module from JSON."""

import argparse
import sys
from pathlib import Path

from .jsonf import _declaration_from_json, _write_declaration


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='typeshi', description=__doc__)
    parser.add_argument('input', type=Path, help='JSON object or nonempty array of records')
    parser.add_argument('--name', required=True, help='name of the generated root or record type')
    parser.add_argument('-o', '--output', type=Path, help='output file (default: standard output)')
    parser.add_argument('--no-literals', action='store_true', help='infer scalar types instead of literal values')
    parser.add_argument('--check', action='store_true', help='exit 1 if the output is missing or stale')
    args = parser.parse_args(argv)
    if args.check and args.output is None:
        parser.error('--check requires --output')

    try:
        source = _declaration_from_json(args.name, args.input, literals_where_possible=not args.no_literals)
        if args.output is None:
            sys.stdout.write(source)
            return 0
        if args.output.exists() and args.output.samefile(args.input):
            parser.error('input and output must be different files')
        if args.check:
            if args.output.exists() and not args.output.is_file():
                parser.error(f'expected a regular output file: {args.output}')
            try:
                contents = args.output.read_bytes()
            except FileNotFoundError:
                print(f'{args.output} is missing', file=sys.stderr)
                return 1
            if contents.replace(b'\r\n', b'\n') != source.encode('utf-8'):
                print(f'{args.output} is stale', file=sys.stderr)
                return 1
        else:
            _write_declaration(args.output, source)
    except (OSError, ValueError, TypeError, RecursionError) as error:
        parser.exit(2, f'typeshi: {error}\n')
    return 0
