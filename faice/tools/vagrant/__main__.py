import os
from argparse import ArgumentParser

from faice.helpers import print_user_text
from faice.tools.cli_funcs import read_file, validate, parse, vagrant


def main():
    parser = ArgumentParser(
        description='Generate configuration files to set up an execution engine in a Vagrant virtual machine.'
    )
    parser.add_argument(
        'experiment_file', nargs=1,
        help='Read experiment FILE from a url or a file system path.'
    )
    parser.add_argument(
        '-o', '--output-directory', dest='output_directory', metavar='DIR', default=os.getcwd(),
        help='Choose alternative output DIR for generated configuration files.'
    )
    parser.add_argument(
        '-r', '--remote-data', dest='remote_data', action='store_true',
        help='Use remote data repositories for input file downloads and result file uploads '
        'instead of using local file system paths.'
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

    output_directory = os.path.expanduser(args.output_directory)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    elif not os.path.isdir(output_directory):
        print_user_text([
            '',
            'ERROR: Specified output-directory path already exists, but is not a directory.'
        ], error=True)
        exit(1)

    vagrant(d, output_directory=output_directory, remote_data=args.remote_data)


if __name__ == '__main__':
    main()
