import json
from argparse import ArgumentParser

from faice.helpers import load_local, load_url
from faice.experiments import validate_experiment
from faice.engines import get_engine


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

    args = parser.parse_args()

    d = None
    if args.experiment_file:
        raw = load_local(args.experiment_file)
        d = json.loads(raw)
    elif args.experiment_url:
        raw = load_url(args.experiment_url)
        d = json.loads(raw)

    validate_experiment(d)
    engine = get_engine(d)
    engine.run(d)


if __name__ == '__main__':
    main()
