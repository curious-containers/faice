import json
import sys
from argparse import ArgumentParser

from faice.experiments import validate_experiment, write_experiment_file
from faice.templates import find_variables, fill_template
from faice.helpers import load_local, load_url, print_user_text


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
        '-o', '--output-file', dest='output_file', metavar='FILE', required=True,
        help='write resulting experiment to a JSON formatted FILE'
    )

    parser.add_argument(
        '-n', '--non-interactive', dest='non_interactive', action='store_true',
        help='do not provide an interactive cli prompt to parse undeclared variables and instead provide a JSON '
             'document via stdin'
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
                    print_user_text(
                        ['missing variable {} in json document provided via stdin'.format(variable)],
                        error=True
                    )
                    exit(1)
            template = fill_template(template, fillers)
        else:
            fillers = {}
            for variable in variables:
                fillers[variable] = input("{}: ".format(variable))
            template = fill_template(template, fillers)
            print_user_text([''])

    d = json.loads(template)
    validate_experiment(d)

    write_experiment_file(d, args.output_file)


if __name__ == '__main__':
    main()
