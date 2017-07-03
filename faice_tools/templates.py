import os
import json
import requests
from jinja2 import Template, Environment, meta


def load_template_file(template_file):
    with open(os.path.expanduser(template_file)) as f:
        return f.read()


def load_template_url(template_url):
    r = requests.get(template_url)
    r.raise_for_status()
    return r.text


def find_variables(template):
    environment = Environment()
    ast = environment.parse(template)
    variables = list(meta.find_undeclared_variables(ast))
    variables.sort(reverse=True)
    return variables


def fill_template(template, fillers):
    t = Template(template)
    return t.render(fillers)


def write_experiment_file(experiment, experiment_file):
    with open(os.path.expanduser(experiment_file), 'w') as f:
        json.dump(experiment, f, indent=4)
