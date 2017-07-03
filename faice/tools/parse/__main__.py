import json
import sys
from argparse import ArgumentParser

from faice.experiments import validate_experiment, write_experiment_file
from faice.templates import find_variables, fill_template
from faice.helpers import load_local, load_url


def main():
    parser = ArgumentParser(
        description='parse experiment template to fill in undeclared variables'
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '-u', '--template-url', dest='template_url', metavar='URL',
        help='fetch experiment template from http or https URL'
    )
    input_group.add_argument(
        '-f', '--template-file', dest='template_file', metavar='FILE',
        help='read experiment template from local FILE'
    )

    parser.add_argument(
        '-o', '--output-file', dest='output_file', metavar='FILE',
        help="""write resulting experiment to a FILE;
             experiment will be written to stdout, if no FILE is provided"""
    )

    parser.add_argument(
        '-n', '--non-interactive', dest='non_interactive', action='store_true',
        help="""do not provide an interactive cli prompt to parse undeclared variables;
        relies on a json document provided via stdin"""
    )

    args = parser.parse_args()

    template = None
    if args.template_file:
        template = load_local(args.template_file)
    elif args.template_url:
        template = load_url(args.template_url)

    variables = find_variables(template)

    if variables:
        if args.non_interactive:
            stdin = sys.stdin.read()
            fillers = json.loads(stdin)
            for variable in variables:
                if variable not in fillers:
                    print('missing variable {} in json document provided via stdin'.format(variable), file=sys.stderr)
                    exit(1)
            template = fill_template(template, fillers)
        else:
            fillers = {}
            for variable in variables:
                fillers[variable] = input("{}: ".format(variable))
            template = fill_template(template, fillers)

    d = json.loads(template)
    validate_experiment(d)

    if args.output_file:
        write_experiment_file(d, args.output_file)
    else:
        print(json.dumps(d, indent=4))

if __name__ == '__main__':
    main()
