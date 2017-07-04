import os
import sys
import json
from argparse import ArgumentParser

from faice.helpers import load_local, load_url
from faice.experiments import validate_experiment
from faice.engines import get_engine


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

    args = parser.parse_args()

    output_directory = os.path.expanduser(args.output_directory)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    elif not os.path.isdir(output_directory):
        print('specified output-directory path already exists, but is not a directory', file=sys.stderr)
        sys.exit(1)

    d = None
    if args.experiment_file:
        raw = load_local(args.experiment_file)
        d = json.loads(raw)
    elif args.experiment_url:
        raw = load_url(args.experiment_url)
        d = json.loads(raw)

    validate_experiment(d)
    engine = get_engine(d)
    engine.vagrant(d, output_directory)

    print('files have been written successfully')
    print('run: vagrant up --provider virtualbox')


if __name__ == '__main__':
    main()
