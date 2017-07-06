import json
from argparse import ArgumentParser

from faice.helpers import load_local, load_url, print_user_text
from faice.experiments import validate_experiment


def main():
    parser = ArgumentParser(
        description='validate an experiment description with json schemas built into faice'
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

    args = parser.parse_args()

    d = None
    if args.experiment_file:
        raw = load_local(args.experiment_file)
        d = json.loads(raw)
    elif args.experiment_url:
        raw = load_url(args.experiment_url)
        d = json.loads(raw)

    validate_experiment(d)

if __name__ == '__main__':
    main()
