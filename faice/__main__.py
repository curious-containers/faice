import os
import sys
import textwrap
from collections import OrderedDict
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from faice.tools.run.__main__ import main as run_main
from faice.tools.run.__main__ import DESCRIPTION as RUN_DESCRIPTION
from faice.tools.vagrant.__main__ import main as vagrant_main
from faice.tools.vagrant.__main__ import DESCRIPTION as VAGRANT_DESCRIPTION


VERSION = '1.2'

TOOLS = OrderedDict([
    ('run', run_main),
    ('vagrant', vagrant_main)
])


def main():
    description = [
        'FAICE  Copyright (C) 2017  Christoph Jansen',
        '',
        'This program comes with ABSOLUTELY NO WARRANTY. This is free software, and you are welcome to redistribute it'
        'under certain conditions. See the LICENSE file distributed with this software for details.',
    ]
    parser = ArgumentParser(
        description=os.linesep.join([textwrap.fill(block) for block in description]),
        formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '-v', '--version', action='version', version=VERSION
    )
    subparsers = parser.add_subparsers(title="tools")

    sub_parser = subparsers.add_parser('run', help=RUN_DESCRIPTION, add_help=False)
    _ = subparsers.add_parser('vagrant', help=VAGRANT_DESCRIPTION, add_help=False)

    if len(sys.argv) < 2:
        parser.print_help()
        exit()

    _ = parser.parse_known_args()
    sub_args = sub_parser.parse_known_args()

    tool = TOOLS[sub_args[1][0]]
    sys.argv[0] = 'faice {}'.format(sys.argv[1])
    del sys.argv[1]
    exit(tool())


if __name__ == '__main__':
    main()
