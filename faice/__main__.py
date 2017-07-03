import os
import sys
from collections import OrderedDict

from faice.tools.adapt.__main__ import main as adapt_main
from faice.tools.parse.__main__ import main as parse_main
from faice.tools.run.__main__ import main as run_main
from faice.tools.validate.__main__ import main as validate_main
from faice.tools.vagrant.__main__ import main as vagrant_main


TOOLS = OrderedDict([
    ('parse', parse_main),
    ('adapt', adapt_main),
    ('validate', validate_main),
    ('vagrant', vagrant_main),
    ('run', run_main)
])


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in TOOLS:
        print('usage:')
        for key in TOOLS:
            _, tail = os.path.split(sys.argv[0])
            print(tail, key)
        exit(1)

    tool = TOOLS[sys.argv[1]]
    sys.argv[0] = '{} {}'.format(sys.argv[0], sys.argv[1])
    del sys.argv[1]
    tool()

if __name__ == '__main__':
    main()
