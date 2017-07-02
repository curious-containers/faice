import sys

from faice_tools.tools.adapt.__main__ import main as ae_main
from faice_tools.tools.fill.__main__ import main as ft_main
from faice_tools.tools.run.__main__ import main as run_main


def main():
    tools = {
        'adapt': ae_main,
        'fill': ft_main,
        'run': run_main
    }

    if len(sys.argv) < 2 or sys.argv[1] not in tools:
        print('usage:')
        for key in tools:
            print(sys.argv[0], key)
        exit(1)

    tool = tools[sys.argv[1]]
    sys.argv[0] = '{} {}'.format(sys.argv[0], sys.argv[1])
    del sys.argv[1]
    tool()

if __name__ == '__main__':
    main()
