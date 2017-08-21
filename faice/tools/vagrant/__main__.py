import os
from argparse import ArgumentParser

from faice.helpers import print_user_text
from faice.tools.cli_funcs import read_file, validate, parse, vagrant


DESCRIPTION = 'generate configuration files to set up an execution engine in a Vagrant virtual machine'


def main():
    parser = ArgumentParser(
        description=DESCRIPTION
    )
    parser.add_argument(
        'experiment_file', nargs=1,
        help='read experiment FILE from a url or a file system path'
    )
    parser.add_argument(
        '-o', '--output-directory', dest='output_directory', metavar='DIR', default=os.getcwd(),
        help='choose alternative output DIR for generated configuration files'
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-r', '--remote-data', dest='remote_data', action='store_true',
        help='use remote data repositories for input file downloads and result file uploads instead of using local '
             'file system paths'
    )
    group.add_argument(
        '-i', '--remote-input-data', dest='remote_input_data', action='store_true',
        help='use remote data repositories for input file downloads, but use local file system paths to store result '
             'files'
    )
    parser.add_argument(
        '-n', '--non-interactive', dest='non_interactive', action='store_true',
        help='do not provide an interactive cli prompt to set undeclared variables and instead load a JSON '
             'document containing all values via stdin'
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

    vagrant(
        d,
        output_directory=output_directory,
        remote_input_data=args.remote_input_data or args.remote_data,
        remote_result_data=args.remote_data
    )


if __name__ == '__main__':
    main()
