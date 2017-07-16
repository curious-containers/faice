import sys
from traceback import format_exc


from faice import resources, engines, templates, experiments
from faice.helpers import print_user_text


def _graceful_exception(error_text):
    """function decorator"""
    def dec(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                print(file=sys.stderr)
                print(format_exc(), file=sys.stderr)
                print_user_text([
                    'ERROR: {} For detailed information examine the exception output above.'.format(error_text)
                ], error=True)
                exit(1)
        return wrapper
    return dec


@_graceful_exception('Could not read file.')
def load_local(file_path):
    return resources.load_local(file_path)


@_graceful_exception('Could not load file from URL.')
def load_url(url):
    return resources.load_url(url)


@_graceful_exception('Could not run experiment.')
def run(d):
    engines.run(d)


@_graceful_exception('Could not setup vagrant.')
def vagrant(d, output_directory, use_local_data):
    engines.vagrant(d, output_directory, use_local_data)


@_graceful_exception('Could not parse experiment file.')
def parse(template, non_interactive=False):
    return templates.parse(template, non_interactive=non_interactive)


@_graceful_exception('Experiment format is invalid.')
def validate(d):
    experiments.validate(d)
