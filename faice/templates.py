import sys
import json
from copy import deepcopy
from jinja2 import Template, Environment, meta

from faice.helpers import print_user_text


def parse(template, non_interactive=False):
    variables = _find_variables(template)
    if variables:
        if non_interactive:
            stdin = sys.stdin.read()
            inputs = json.loads(stdin)
            template = _fill_template(template, variables, inputs)
        else:
            print_user_text([
                'The given experiment file contains undeclared variables. Variables are usually used to replace '
                'secret credentials for online services like an execution engine or data repositories. If any of these '
                'credentials are unknown, it might not be possible to run the experiment. Online services can be '
                'avoided by using "faice vagrant".',
                '',
                'Set variables...',
                ''
            ])
            inputs = {}
            for variable in variables:
                inputs[variable] = input('{}: '.format(variable))
            template = _fill_template(template, variables, inputs)

    return json.loads(template)


def _find_variables(template):
    environment = Environment()
    ast = environment.parse(template)
    variables = list(meta.find_undeclared_variables(ast))
    variables.sort(reverse=True)
    return variables


def _fill_template(template, variables, inputs):
    c = deepcopy(inputs)
    for variable in variables:
        if not c.get(variable):
            c[variable] = 'null'
    t = Template(template)
    return t.render(c)
