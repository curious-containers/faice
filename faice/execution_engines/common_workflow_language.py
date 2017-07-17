import os
import yaml
import jsonschema
from copy import deepcopy

from faice.resources import load_local, load_url
from faice.helpers import print_user_text
from faice.schemas import src_code_schema

_engine_config_schema = {
    'type': 'object',
    'properties': {
        'install_requirements': {
            'type': 'object',
            'properties': {
                'cwltool_version': {'type': 'string'}
            },
            'required': ['cwltool_version'],
            'additionalProperties': False
        }
    },
    'required': ['install_requirements'],
    'additionalProperties': False
}

_instructions_schema = {
    'type': 'object',
    'properties': {
        'cwl_file': {
            'oneOf': [{
                'type': 'object',
                'properties': {
                    'url': {'type': 'string'}
                },
                'required': ['url'],
                'additionalProperties': False
            }, {
                'type': 'object',
                'properties': {
                    'path': {'type': 'string'}
                },
                'required': ['path'],
                'additionalProperties': False
            }]
        },
        'cwl_input_file': {
            'oneOf': [{
                'type': 'object',
                'properties': {
                    'url': {'type': 'string'}
                },
                'required': ['url'],
                'additionalProperties': False
            }, {
                'type': 'object',
                'properties': {
                    'path': {'type': 'string'}
                },
                'required': ['path'],
                'additionalProperties': False
            }]
        }
    },
    'required': ['cwl_file', 'cwl_input_file'],
    'additionalProperties': False
}

_meta_data_schema = {
    'type': 'object',
    'properties': {
        'applications': {
            'type': 'object',
            'patternProperties': {
                '^[a-zA-Z0-9.:/-]+$': src_code_schema
            },
            'additionalProperties': False
        }
    },
    'additionalProperties': False
}


def validate_engine_config(d):
    engine_config = d['execution_engine']['engine_config']
    jsonschema.validate(engine_config, _engine_config_schema)


def _load_cwl_files(d):
    cwl_file_data = d['instructions']['cwl_file']
    cwl_input_file_data = d['instructions']['cwl_input_file']
    results = []
    for file_data in [cwl_file_data, cwl_input_file_data]:
        if file_data.get('url'):
            text = load_url(file_data['url'])
        else:
            text = load_local(file_data['path'])
        yaml_data = yaml.load(text)
        results.append(yaml_data)
    return results


def validate_instructions(d):
    instructions = d['instructions']
    jsonschema.validate(instructions, _instructions_schema)


def validate_meta_data(d):
    meta_data = d['meta_data']
    jsonschema.validate(meta_data, _meta_data_schema)
    _ = _load_cwl_files(d)


def run(d):
    raise Exception(
        'The "faice run" tool is not available with the common-workflow-language execution engine. '
        'Try using "faice vagrant" instead.'
    )


def _adapt_for_vagrant(cwl_input_yaml):
    c = deepcopy(cwl_input_yaml)

    for key, val in c.items():
        if isinstance(val, dict) and val['class'] == 'File':
            val['path'] = '/vagrant/inputs/{}'.format(key)

    return c


def vagrant(d, output_directory, use_local_data):
    engine_config = d['execution_engine']['engine_config']

    cwltool_version = engine_config['install_requirements']['cwltool_version']

    vm_memory = 4096
    vm_cpus = 2
    vm_box = 'trusty64'
    vm_box_url = 'https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-vagrant.box'
    vm_user = 'ubuntu'

    vagrant_file_name = 'Vagrantfile'
    provision_file_name = 'provision.sh'
    cwl_file_name = 'experiment.cwl'
    cwl_input_file_name = 'experiment-cwl-input.yml'

    cwl_yaml, cwl_input_yaml = _load_cwl_files(d)

    vagrant_file_lines = [
        'VAGRANTFILE_API_VERSION = "2"',
        '',
        'Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|',
        '    config.vm.box = "{}"'.format(vm_box),
        '    config.vm.box_url = "{}"'.format(vm_box_url),
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
        'apt-get update',
        'apt-get install -y docker.io python-pip',
        '',
        'usermod -aG docker {}'.format(vm_user),
        '',
        'pip install "cwltool=={}"'.format(cwltool_version),
        '',
        'echo',
        'echo setup successful',
        'echo',
        'echo run application...'
        'echo',
        '',
        'cd /vagrant/outputs',
        'cwltool /vagrant/experiment.cwl /vagrant/experiment-cwl-input.yml',
        ''
    ]

    files = [
        (vagrant_file_name, vagrant_file_lines),
        (provision_file_name, provision_file_lines)
    ]

    for file_name, file_lines in files:
        file_content = os.linesep.join(file_lines)
        file_path = os.path.join(output_directory, file_name)
        with open(file_path, 'w') as f:
            f.write(file_content)

    cwl_input_yaml_copy = _adapt_for_vagrant(cwl_input_yaml)
    with open(os.path.join(output_directory, cwl_input_file_name), 'w') as f:
        yaml.dump(cwl_input_yaml_copy, f)

    with open(os.path.join(output_directory, cwl_file_name), 'w') as f:
        yaml.dump(cwl_yaml, f)

    directories = {
        'inputs': os.path.join(output_directory, 'inputs'),
        'outputs': os.path.join(output_directory, 'outputs')
    }

    for _, directory in directories.items():
        if not os.path.exists(directory):
            os.makedirs(directory)

    user_text = []

    if use_local_data:
        user_text += [
            '',
            'The option --use-local-data has been set. This setting is ignored by the common-workflow-language '
            'execution engine'
        ]

    user_text += [
        '',
        'STEP 1: It is required, that the input files listed below are copied to the appropriate file system locations '
        'before running the experiment:'
    ]

    for key, val in cwl_input_yaml_copy.items():
        if isinstance(val, dict) and val['class'] == 'File':
            file_path = os.path.join(directories['inputs'], str(key))
            doc = cwl_yaml['inputs'][key].get('doc')

            user_text.append('')
            if doc:
                user_text.append('file description: {}'.format(doc))
            user_text.append('file location: {}'.format(file_path))

    user_text += [
        '',
        'The result files will be written to the {} directory'.format(directories['outputs']),
        '',
        'STEP 2: Change to the {} directory and run:'.format(output_directory),
        '',
        'vagrant up --provider virtualbox',
        '',
        'This will start a virtual machine, containing the common-workflow-language execution engine. Vagrant and '
        'VirtualBox are required beforehand.',
        '',
        'The experiment will run automatically during the vagrant virtual machine provisioning.',
        ''
    ]

    print_user_text(user_text)
