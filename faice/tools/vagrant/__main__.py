import os
import sys
from argparse import ArgumentParser

from faice.helpers import load_local, load_url, print_user_text
from faice.experiments import validate_experiment
from faice.engines import get_engine
from faice.templates import parse


def main():
    parser = ArgumentParser(
        description='generate files to set up an execution engine in a Vagrant virtual machine'
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
        '-o', '--output-directory', dest='output_directory', metavar='DIRECTORY', required=True,
        help='save generated files in a DIRECTORY'
    )

    parser.add_argument(
        '-l', '--use-local-data', dest='use_local_data', action='store_true',
        help='change references pointing to remote input and result files '
             'to local references in the generated experiment.json file'
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
    validate_experiment(d)
    engine = get_engine(d)

    output_directory = os.path.expanduser(args.output_directory)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    elif not os.path.isdir(output_directory):
        user_text = ['specified output-directory path already exists, but is not a directory']
        print_user_text(user_text, error=True)
        sys.exit(1)

    engine.vagrant(d, output_directory=output_directory, use_local_data=args.use_local_data)


if __name__ == '__main__':
    main()
