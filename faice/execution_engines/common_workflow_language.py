import os
import yaml
import jsonschema
from copy import deepcopy

from faice.resources import read_local, read_url
from faice.helpers import print_user_text
from faice.schemas import src_code_schema

_engine_config_schema = {
    'type': 'object',
    'properties': {
        'install_requirements': {
            'type': 'object',
            'properties': {
                'cwltool_version': {'type': 'string'},
                'host_ram': {'type': 'integer'},
                'host_cpus': {'type': 'integer'}
            },
            'required': ['cwltool_version', 'host_ram', 'host_cpus'],
            'additionalProperties': False
        }
    },
    'required': ['install_requirements'],
    'additionalProperties': False
}

_yaml_reference_schema = {
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
    }, {
        'type': 'object',
        'properties': {
            'yaml': {'type': 'string'}
        },
        'required': ['yaml'],
        'additionalProperties': False
    }]
}

_instructions_schema = {
    'type': 'object',
    'properties': {
        'cwl_file': _yaml_reference_schema,
        'cwl_input_file': _yaml_reference_schema
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
        },
        'input_files': {
            'type': 'object',
            'patternProperties': {
                '^[a-zA-Z0-9._-]+$': {
                    'type': 'object',
                    'properties': {
                        'file_extension_preference': {'type': 'string'}
                    },
                    'required': ['file_extension_preference'],
                    'additionalProperties': False
                }
            },
            'additionalProperties': False
        },
        'output_files': {
            'type': 'object',
            'patternProperties': {
                '^[a-zA-Z0-9._-]+$': {
                    'type': 'object',
                    'properties': {
                        'file_extension_preference': {'type': 'string'}
                    },
                    'required': ['file_extension_preference'],
                    'additionalProperties': False
                }
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
            text = read_url(file_data['url'])
        elif file_data.get('path'):
            text = read_local(file_data['path'])
        else:
            text = file_data['yaml']
        yaml_data = yaml.load(text)
        results.append(yaml_data)
    return results


def validate_instructions(d):
    instructions = d['instructions']
    jsonschema.validate(instructions, _instructions_schema)


def validate_meta_data(d):
    meta_data = d['meta_data']
    jsonschema.validate(meta_data, _meta_data_schema)
    cwl_yaml, cwl_input_yaml = _load_cwl_files(d)

    for key, val in cwl_input_yaml.items():
        if key not in cwl_yaml['inputs']:
            raise Exception('Key {} from input file not found in cwl file.'.format(key))

    for key, val in cwl_yaml['inputs'].items():
        if 'File' in val['type']:
            if key not in meta_data['input_files']:
                raise Exception(
                    'Key {} from cwl file inputs does not have a corresponding entry in meta_data input_files.'
                    ''.format(key)
                )

    for key, val in cwl_yaml['outputs'].items():
        if 'File' in val['type']:
            if key not in meta_data['output_files']:
                raise Exception(
                    'Key {} from cwl file outputs does not have a corresponding entry in meta_data output_files.'
                    ''.format(key)
                )


def run(d):
    raise Exception(
        'The "faice run" tool is not available with the common-workflow-language execution engine. '
        'Try using "faice vagrant" instead.'
    )


def _adapt_for_vagrant(cwl_input_yaml, meta_data):
    c = deepcopy(cwl_input_yaml)

    for key, val in c.items():
        if isinstance(val, dict) and val['class'] == 'File':
            val['path'] = '/vagrant/inputs/{}.{}'.format(
                key,
                meta_data['input_files'][key]['file_extension_preference']
            )

    return c


def vagrant(d, output_directory, remote_data):
    engine_config = d['execution_engine']['engine_config']

    cwltool_version = engine_config['install_requirements']['cwltool_version']

    vm_memory = engine_config['install_requirements']['host_ram']
    vm_cpus = engine_config['install_requirements']['host_cpus']
    vm_box = 'trusty64'
    vm_box_url = 'https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-vagrant.box'
    vm_user = 'ubuntu'

    vagrant_file_name = 'Vagrantfile'
    provision_file_name = 'provision.sh'
    cwl_file_name = 'experiment.cwl'
    cwl_input_file_name = 'experiment-cwl-input.yml'
    readme_file_name = 'README.txt'

    directories = {
        'inputs': os.path.join(output_directory, 'inputs'),
        'outputs': os.path.join(output_directory, 'outputs')
    }

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
        'echo run application...',
        'echo',
        '',
        'cd /vagrant/outputs',
        'cwltool /vagrant/experiment.cwl /vagrant/experiment-cwl-input.yml',
        ''
    ]

    meta_data = d['meta_data']
    cwl_input_yaml_copy = _adapt_for_vagrant(cwl_input_yaml, meta_data)

    readme_file_lines = []

    if remote_data:
        readme_file_lines += [
            '',
            'The --remote-data flag has been set, but is not supported with the common-workflow-language execution'
            'engine and will be ignored.'
        ]

    readme_file_lines += [
        '',
        'STEP 1: It is required, that the input files listed below are copied to the appropriate file system locations '
        'before running the experiment:'
    ]

    for key, val in cwl_input_yaml_copy.items():
        if isinstance(val, dict) and val['class'] == 'File':
            file_name = '{}.{}'.format(
                key,
                meta_data['input_files'][key]['file_extension_preference']
            )
            file_path = os.path.join(directories['inputs'], file_name)
            doc = cwl_yaml['inputs'][key].get('doc')

            readme_file_lines.append('')
            if doc:
                readme_file_lines.append('file doc: {}'.format(doc))
            readme_file_lines.append('file location: {}'.format(file_path))

    readme_file_lines += [
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

    # create files and directories
    files = [
        (vagrant_file_name, vagrant_file_lines),
        (provision_file_name, provision_file_lines),
        (readme_file_name, readme_file_lines)
    ]

    for file_name, file_lines in files:
        file_content = os.linesep.join(file_lines)
        file_path = os.path.join(output_directory, file_name)
        with open(file_path, 'w') as f:
            f.write(file_content)

    with open(os.path.join(output_directory, cwl_input_file_name), 'w') as f:
        yaml.dump(cwl_input_yaml_copy, f)

    with open(os.path.join(output_directory, cwl_file_name), 'w') as f:
        yaml.dump(cwl_yaml, f)

    for _, directory in directories.items():
        if not os.path.exists(directory):
            os.makedirs(directory)

    # print readme
    print_user_text(readme_file_lines)
