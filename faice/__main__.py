import os
import sys
from collections import OrderedDict

from faice.tools.run.__main__ import main as run_main
from faice.tools.vagrant.__main__ import main as vagrant_main
from faice.helpers import print_user_text


TOOLS = OrderedDict([
    ('run', run_main),
    ('vagrant', vagrant_main)
])


def _user_text():
    result = [
        'FAICE  Copyright (C) 2017  Christoph Jansen',
        '',
        'This program comes with ABSOLUTELY NO WARRANTY. This is free software, and you are welcome to redistribute it'
        'under certain conditions. See the LICENSE file distributed with this software for details.',
        '',
        'usage:',
        '',
    ]

    for key in TOOLS:
        _, tail = os.path.split(sys.argv[0])
        result.append('{} {}'.format(tail, key))

    return result


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in TOOLS:
        user_text = _user_text()
        print_user_text(user_text)
        exit(1)

    tool = TOOLS[sys.argv[1]]
    sys.argv[0] = '{} {}'.format(sys.argv[0], sys.argv[1])
    del sys.argv[1]
    tool()

if __name__ == '__main__':
    main()
