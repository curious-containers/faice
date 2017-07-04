import os
import requests
import jsonschema
from copy import deepcopy
from pprint import pprint

from faice.helpers import find_open_port


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


def adapt(d, use_local_execution_engine=False, use_local_input_files=False, use_local_result_files=False):
    c = deepcopy(d)

    if use_local_execution_engine:
        c['experiment']['execution_engine']['engine_config'] = {
            'url': 'http://localhost:8000',
            'auth': {
                'username': 'user',
                'password': 'PASSWORD'
            }
        }

    if use_local_input_files:
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

    if use_local_result_files:
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


def vagrant(d, output_directory):
    engine_config = d['experiment']['execution_engine']['engine_config']

    cc_server_version = engine_config['install_requirements']['cc_server_version']
    docker_compose_version = '1.14.0'

    cc_host_port = find_open_port()
    cc_guest_port = 8000
    vm_memory = 4096
    vm_cpus = 2
    vm_box = 'trusty64'
    vm_box_url = 'https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-vagrant.box',
    vm_user = 'ubuntu'

    vagrant_file_name = 'Vagrantfile'
    provision_file_name = 'provision.sh'
    compose_file_name = 'docker-compose.yml'

    vagrant_file_lines = [
        'VAGRANTFILE_API_VERSION = "2"',
        '',
        'Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|',
        '    config.vm.box = "{}"'.format(vm_box),
        '    config.vm.box_url = "{}"'.format(vm_box_url),
        '    config.vm.network :forwarded_port, guest: {}, host: {}'.format(cc_guest_port, cc_host_port),
        '',
        '    config.vm.provider "virtualbox" do |v|',
        '        v.memory = {}'.format(vm_memory),
        '        v.customize ["modifyvm", :id, "--cpus", "{}"]'.format(vm_cpus),
        '    end',
        '',
        '    config.vm.provision "shell", path: "{}"'.format(provision_file_name),
        'end',
        ''
    ]

    provision_file_lines = [
        '#!/usr/bin/env bash',
        '',
        '# bash strict mode',
        'set -euo pipefail',
        '',
        'apt-get update',
        'apt-get install -y git docker.io',
        '',
        'usermod -aG docker {}'.format(vm_user),
        '',
        'curl -L https://github.com/docker/compose/releases/download/{}/docker-compose-$(uname -s)-$(uname -m) '
        '> /usr/local/bin/docker-compose'.format(docker_compose_version),
        'chmod +x /usr/local/bin/docker-compose',
        '',
        'su {}'.format(vm_user),
        'cd ~',
        'git clone -b {} --depth 1 https://github.com/curious-containers/cc-server.git'.format(cc_server_version),
        ''
    ]

    compose_file_lines = [
        'version: "2"',
        'services:',
        '  cc-server-web:',
        '    build: ./cc-server-image',
        '    command: "python3 -u /root/.config/curious-containers/cc-server-web/init.py"',
        '    ports:',
        '      - "8000:8000"',
        '    volumes:',
        '      - ../cc_server_web:/opt/cc_server_web:ro',
        '      - ../cc_commons:/opt/cc_commons:ro',
        '      - .:/root/.config/curious-containers:ro',
        '    links:',
        '      - mongo',
        '      - cc-server-master',
        '      - cc-server-log',
        '    tty: true',
        ''
    ]

    files = [
        (vagrant_file_name, vagrant_file_lines),
        (provision_file_name, provision_file_lines),
        (compose_file_name, compose_file_lines)
    ]

    for file_name, file_lines in files:
        file_content = os.linesep.join(file_lines)
        file_path = os.path.join(output_directory, file_name)
        with open(file_path, 'w') as f:
            f.write(file_content)
