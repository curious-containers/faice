from jinja2 import Template, Environment, meta


def find_variables(template):
    environment = Environment()
    ast = environment.parse(template)
    variables = list(meta.find_undeclared_variables(ast))
    variables.sort(reverse=True)
    return variables


def fill_template(template, fillers):
    t = Template(template)
    return t.render(fillers)
