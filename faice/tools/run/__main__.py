from argparse import ArgumentParser

from faice.tools.cli_funcs import load_url, load_local, validate, parse, run


def main():
    parser = ArgumentParser(
        description='run the specified experiment in an execution engine'
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '-u', '--experiment-url', dest='experiment_url', metavar='URL',
        help='fetch experiment from http or https URL'
    )
    input_group.add_argument(
        '-f', '--experiment-file', dest='experiment_file', metavar='FILE',
        help='read experiment from local FILE'
    )

    parser.add_argument(
        '-n', '--non-interactive', dest='non_interactive', action='store_true',
        help='do not provide an interactive cli prompt to set undeclared variables and instead load a JSON '
             'document containing the variables with their respective values via stdin'
    )

    args = parser.parse_args()

    experiment = None
    if args.experiment_file:
        experiment = load_local(args.experiment_file)
    elif args.experiment_url:
        experiment = load_url(args.experiment_url)

    d = parse(experiment, non_interactive=args.non_interactive)
    validate(d)
    run(d)


if __name__ == '__main__':
    main()
