from argparse import ArgumentParser

from faice.tools.cli_funcs import read_file, validate, parse, run


def main():
    parser = ArgumentParser(
        description='Run an experiment with the specified execution engine.'
    )
    parser.add_argument(
        'experiment_file', nargs=1,
        help='Read experiment FILE from a url or a file system path.'
    )
    parser.add_argument(
        '-n', '--non-interactive', dest='non_interactive', action='store_true',
        help='Do not provide an interactive cli prompt to set undeclared variables and instead load a JSON '
             'document containing all values via stdin.'
    )

    args = parser.parse_args()

    experiment = read_file(args.experiment_file[0])

    d = parse(experiment, non_interactive=args.non_interactive)
    validate(d)
    run(d)


if __name__ == '__main__':
    main()
