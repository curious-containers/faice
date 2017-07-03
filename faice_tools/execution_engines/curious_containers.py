import requests
import jsonschema
from copy import deepcopy
from pprint import pprint


_engine_config_schema = {
    'type': 'object',
    'properties': {
        'url': {'type': 'string'},
        'auth': {
            'type': 'object',
            'properties': {
                'username': {'type': 'string'},
                'password': {'type': 'string'}
            },
            'required': ['username', 'password'],
            'additionalProperties': False
        },
        'install_requirements': {
            'type': 'object',
            'properties': {
                'cc_server_version': {'type': 'string'}
            },
            'required': ['cc_server_version'],
            'additionalProperties': False
        }
    },
    'required': ['url', 'auth', 'install_requirements'],
    'additionalProperties': False
}


def validate_engine_config(d):
    engine_config = d['experiment']['execution_engine']['engine_config']
    jsonschema.validate(engine_config, _engine_config_schema)
    validated = True
    return validated


def validate_instructions(d):
    engine_config = d['experiment']['execution_engine']['engine_config']
    instructions = d['experiment']['instructions']
    url = engine_config['url'].rstrip('/')
    auth = (engine_config['auth']['username'], engine_config['auth']['password'])
    r = requests.get('{}/tasks/schema'.format(url), auth=auth)
    try:
        r.raise_for_status()
    except:
        return False
    instructions_schema = r.json()
    jsonschema.validate(instructions, instructions_schema)
    return True


def run(d):
    engine_config = d['experiment']['execution_engine']['engine_config']
    instructions = d['experiment']['instructions']
    url = engine_config['url'].rstrip('/')
    auth = (engine_config['auth']['username'], engine_config['auth']['password'])
    r = requests.post('{}/tasks'.format(url), auth=auth, json=instructions)
    r.raise_for_status()
    pprint(r.json())


def adapt(d, options):
    c = deepcopy(d)

    if options.get('use_local_execution_engine'):
        c['experiment']['execution_engine']['engine_config'] = {
            'url': 'http://localhost:8000',
            'auth': {
                'username': 'user',
                'password': 'PASSWORD'
            }
        }

    if options.get('use_local_input_files'):
        if c['experiment']['instructions'].get('tasks'):
            tasks = c['experiment']['instructions']['tasks']
        else:
            tasks = [c['experiment']['instructions']]
        for task in tasks:
            for i, input_file in enumerate(task['input_files']):
                input_file['connector_type'] = 'http'
                input_file['connector_access'] = {
                    'url': 'http://file-server/{}'.format(i),
                    'method': 'GET'
                }

    if options.get('use_local_result_files'):
        if c['experiment']['instructions'].get('tasks'):
            tasks = c['experiment']['instructions']['tasks']
        else:
            tasks = [c['experiment']['instructions']]

        for task in tasks:
            result_file_names = {result_file['local_result_file'] for result_file in task['result_files']}
            task['result_files'] = [
                {
                    'local_result_file': result_file_name,
                    'connector_type': 'http',
                    'connector_access': {
                        'url': 'http://file-server/{}'.format(result_file_name),
                        'method': 'POST'
                    }
                }
                for result_file_name in result_file_names
            ]

    return c


def vagrant(d):
    pass
