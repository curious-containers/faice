from argparse import ArgumentParser

from faice_tools.tools.fill.template import load_template_file, load_template_url
from faice_tools.tools.fill.template import find_variables, fill_template
from faice_tools.tools.fill.template import write_experiment_file


def main():
    parser = ArgumentParser(description='fill undeclared variables in an experiment template')

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
        help='write resulting experiment to a FILE'
    )

    args = parser.parse_args()

    template = None
    if args.template_file:
        template = load_template_file(args.template_file)
    elif args.template_url:
        template = load_template_url(args.template_url)

    variables = find_variables(template)
    fillers = {}
    for variable in variables:
        fillers[variable] = input("{}: ".format(variable))

    experiment = fill_template(template, fillers)
    write_experiment_file(experiment, args.output_file)

if __name__ == '__main__':
    main()
