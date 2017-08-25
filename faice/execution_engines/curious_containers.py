import os
import json
import requests
import jsonschema
from copy import deepcopy
from pprint import pprint

from faice.helpers import print_user_text, Stepper
from faice.resources import find_open_port
from faice.schemas import src_code_schema, doc_array_schema, doc_object_schema


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
                'cc_server_version': {'enum': ['0.12']},
                'host_ram': {'type': 'integer'},
                'host_cpus': {'type': 'integer'}
            },
            'required': ['cc_server_version', 'host_ram', 'host_cpus'],
            'additionalProperties': False
        }
    },
    'required': ['install_requirements'],
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
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'doc': {'type': 'string'},
                    'file_extension_preference': {'type': 'string'}
                },
                'required': ['doc', 'file_extension_preference'],
                'addtionalProperties': False
            }
        },
        'result_files': {
            'type': 'object',
            'patternProperties': {
                '^[a-zA-Z0-9._-]+$': {
                    'type': 'object',
                    'properties': {
                        'doc': {'type': 'string'},
                        'is_optional': {'type': 'boolean'},
                        'file_extension_preference': {'type': 'string'}
                    },
                    'required': ['doc', 'is_optional', 'file_extension_preference'],
                    'additionalProperties': False
                }
            },
            'additionalProperties': False
        },
        'parameters': {
            'type': 'object',
            'properties': {
                'is_optional': {'type': 'boolean'},
                'docs': {
                    'oneOf': [
                        doc_array_schema,
                        doc_object_schema
                    ]
                }
            },
            'required': ['docs', 'is_optional'],
            'additionalProperties': False
        }
    },
    'required': ['input_files', 'result_files'],
    'additionalProperties': False
}


def validate_engine_config(d):
    engine_config = d['execution_engine']['engine_config']
    jsonschema.validate(engine_config, _engine_config_schema)


def validate_instructions(d):
    engine_config = d['execution_engine']['engine_config']
    instructions = d['instructions']
    timeout = (5, 30)

    if instructions.get('tasks'):
        raise Exception(
            'Specifying multiple tasks in instructions is not supported with FAICE.'
        )

    try:
        url = engine_config['url'].rstrip('/')
        auth = (engine_config['auth']['username'], engine_config['auth']['password'])
    except:
        print_user_text([
            '',
            'Instructions could not be validated, because url or auth has not been specified for execution engine.'
        ], error=True)
        return

    try:
        r = requests.get(
            '{}/'.format(url),
            auth=auth,
            timeout=timeout
        )
        r.raise_for_status()
        data = r.json()
        cc_server_version = data['version']
    except:
        print_user_text([
            '',
            'Instructions could not be validated, because version could not be requested from cc-server.'
        ], error=True)
        return

    if cc_server_version != engine_config['install_requirements']['cc_server_version']:
        print_user_text([
            '',
            'Instructions could not be validated, because requested cc-server version does not match '
            'cc_version_version specified in install_requirements.'
        ], error=True)
        return

    try:
        r = requests.get(
            '{}/tasks/schema'.format(url),
            auth=auth,
            timeout=(5, 30)
        )
        r.raise_for_status()
        instructions_schema = r.json()
    except:
        print_user_text([
            '',
            'Instructions could not be validated, because the corrisponding schema file could not be requested '
            'from cc-server.'
        ], error=True)
        return

    jsonschema.validate(instructions, instructions_schema)


def validate_meta_data(d):
    meta_data = d['meta_data']
    jsonschema.validate(meta_data, _meta_data_schema)

    instructions = d['instructions']

    if len(instructions['input_files']) != len(meta_data['input_files']):
        raise Exception(
            'The number of input_files in instructions must be equals the number of input_files in meta_data'
        )

    for result_file in instructions['result_files']:
        local_result_file = result_file['local_result_file']
        if local_result_file not in meta_data['result_files']:
            raise Exception(
                'Key {} from instructions result_files does not have a corresponding entry in meta_data results_files.'
                ''.format(local_result_file)
            )


def run(d):
    engine_config = d['execution_engine']['engine_config']
    instructions = d['instructions']

    if 'url' not in engine_config:
        raise Exception('The engine_config does not provide a url to a Curious Containers server.')
    url = engine_config['url'].rstrip('/')

    auth = None
    if 'auth' in engine_config:
        auth = (engine_config['auth']['username'], engine_config['auth']['password'])

    r = requests.post(
        '{}/tasks'.format(url),
        auth=auth,
        json=instructions,
        timeout=(5, 30)
    )
    r.raise_for_status()
    data = r.json()

    user_text = [
        '',
        'The task has been scheduled with Curious Containers execution engine. It may take some time to finish.',
        '',
        'Response from Curious Containers:'
    ]

    print_user_text(user_text)
    pprint(data)


def _adapt_for_vagrant(d, port, username, password, remote_input_data, remote_result_data):
    c = deepcopy(d)

    c['execution_engine']['engine_config']['url'] = 'http://localhost:{}/cc'.format(port)
    c['execution_engine']['engine_config']['auth'] = {
        'username': username,
        'password': password
    }

    if not remote_input_data:
        if c['instructions'].get('tasks'):
            tasks = c['instructions']['tasks']
        else:
            tasks = [c['instructions']]

        for task in tasks:
            for i, input_file in enumerate(task['input_files']):
                input_file['connector_type'] = 'http'
                input_file['connector_access'] = {
                    'url': 'http://172.17.0.1:8003/{}.{}'.format(
                        i+1,
                        c['meta_data']['input_files'][i]['file_extension_preference']
                    ),
                    'method': 'GET'
                }

    if not remote_result_data:
        if c['instructions'].get('tasks'):
            tasks = c['instructions']['tasks']
        else:
            tasks = [c['instructions']]

        for task in tasks:
            local_result_files = {result_file['local_result_file'] for result_file in task['result_files']}
            task['result_files'] = [
                {
                    'local_result_file': local_result_file,
                    'connector_type': 'http',
                    'connector_access': {
                        'url': 'http://172.17.0.1:8003/{}.{}'.format(
                            local_result_file,
                            c['meta_data']['result_files'][local_result_file]['file_extension_preference']
                        ),
                        'method': 'POST'
                    }
                }
                for local_result_file in local_result_files
            ]

    return c


def vagrant(d, output_directory, remote_input_data, remote_result_data):
    engine_config = d['execution_engine']['engine_config']

    cc_server_version = engine_config['install_requirements']['cc_server_version']

    cc_username = 'ccuser'
    cc_password = 'ccpass'
    cc_host_port = find_open_port()
    cc_ui_url = 'https://github.com/curious-containers/cc-ui/releases/download/0.12/release.tar.gz'
    mongo_db = 'ccdb'
    mongo_username = 'ccdbAdmin'
    mongo_password = 'PASSWORD'
    vm_memory = engine_config['install_requirements']['host_ram']
    vm_cpus = engine_config['install_requirements']['host_cpus']
    vm_box = 'xenial64'
    vm_box_url = 'https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-vagrant.box'

    vagrant_file_name = 'Vagrantfile'
    provision_file_name = 'provision.sh'
    experiment_file_name = 'experiment.json'
    apache_file_name = 'cc-server.conf'
    cc_file_name = 'config.toml'
    credentials_file_name = 'cc-credentials.json'
    readme_file_name = 'README.txt'

    directories = {
        'input_files': os.path.join(output_directory, 'input_files'),
        'result_files': os.path.join(output_directory, 'result_files'),
        'logs': os.path.join(output_directory, 'logs')
    }

    vagrant_file_lines = [
        'VAGRANTFILE_API_VERSION = "2"',
        '',
        'Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|',
        '    config.vm.box = "{}"'.format(vm_box),
        '    config.vm.box_url = "{}"'.format(vm_box_url),
        '    config.vm.network :forwarded_port, guest: 80, host: {}'.format(cc_host_port),
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

    data = {
        'user': mongo_username,
        'pwd': mongo_password,
        'roles': [{
            'role': 'readWrite',
            'db': mongo_db
        }]
    }

    provision_file_lines = [
        '#!/usr/bin/env bash',
        '',
        '# mongo repository',
        'apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv EA312927',
        'echo "deb http://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.2 multiverse" > '
        '/etc/apt/sources.list.d/mongodb-org-3.2.list',
        '',
        '# install dependencies',
        'apt-get update',
        'apt-get install -y curl tar git docker.io apache2 mongodb-org-server mongodb-org-shell '
        'python3-toml python3-jsonschema python3-zmq python3-requests python3-pymongo python3-docker python3-flask '
        'python3-gunicorn python3-cryptography python3-gevent python3-chardet',
        'systemctl enable mongod',
        'systemctl start mongod',
        '',
        '# cc-server',
        'cd',
        'mkdir -p .config/cc-server',
        'cp /vagrant/{} .config/cc-server'.format(cc_file_name),
        'git clone -b {} --depth 1 https://github.com/curious-containers/cc-server.git'.format(cc_server_version),
        'cd cc-server',
        'mongo --eval \'database = db.getSiblingDB("{}"); database.createUser({})\''.format(mongo_db, json.dumps(data)),
        'bash bin/cc-create-systemd-unit-file -d $(pwd)',
        'systemctl enable cc-server',
        'systemctl start cc-server',
        '',
        '# cc-ui',
        'cd',
        'curl -sL {} | tar -xvz'.format(cc_ui_url),
        'mv build /opt/cc-ui',
        'chown -R www-data:www-data /opt/cc-ui',
        '',
        '# apache2',
        'cp /vagrant/{} /etc/apache2/sites-available'.format(apache_file_name),
        'a2enmod proxy_http',
        'a2dissite 000-default',
        'a2ensite cc-server',
        'systemctl restart apache2',
        '',
        '# user account for cc-server',
        'cd ~/cc-server',
        'cat /vagrant/{} | ~/cc-server/bin/cc-create-user-non-interactive'.format(credentials_file_name),
        '',
        '# check web server',
        'http_code=$(curl -sL -w "%{http_code}" http://localhost:8000/ -o /dev/null)',
        'if [ "${http_code}" != "200" ]; then',
        '    echo ERROR: setup failed.',
        '    exit 1',
        'fi',
        '',
        'echo',
        'echo Setup successful.',
        'echo',
        'echo Run the experiment from the generated JSON file:',
        'echo faice run experiment.json',
        ''
    ]

    cc_file_lines = [
        '[server_web]',
        'external_url = "http://172.17.0.1:8000/"',
        'bind_host = "0.0.0.0"',
        'bind_port = 8000',
        '',
        '[server_master]',
        'external_url = "tcp://localhost:8001"',
        'bind_host = "127.0.0.1"',
        'bind_port = 8001',
        'scheduling_interval_seconds = 60',
        '',
        '[server_log]',
        'external_url = "tcp://localhost:8002"',
        'bind_host = "127.0.0.1"',
        'bind_port = 8002',
        'log_dir = "/vagrant/logs"',
        'suppress_stdout = true',
        '',
        '[server_files]',
        'external_url = "http://172.17.0.1:8003"',
        'bind_host = "0.0.0.0"',
        'bind_port = 8003',
        'input_files_dir = "/vagrant/input_files"',
        'result_files_dir = "/vagrant/result_files"',
        '',
        '[mongo]',
        'username = "{}"'.format(mongo_username),
        'password = "{}"'.format(mongo_password),
        'host = "localhost"',
        'port = 27017',
        'db = "{}"'.format(mongo_db),
        '',
        '[docker]',
        'thread_limit = 8',
        'api_timeout = 30',
        '',
        '[docker.nodes.local]',
        'base_url = "unix://var/run/docker.sock"',
        '',
        '[defaults.application_container_description]',
        'entry_point = "python3 -m cc_container_worker.application_container"',
        '',
        '[defaults.data_container_description]',
        'image = "docker.io/curiouscontainers/cc-image-fedora:{}"'.format(cc_server_version),
        'entry_point = "python3 -m cc_container_worker.data_container"',
        'container_ram = 512',
        '',
        '[defaults.inspection_container_description]',
        'image = "docker.io/curiouscontainers/cc-image-fedora:{}"'.format(cc_server_version),
        'entry_point = "python3 -m cc_container_worker.inspection_container"',
        '',
        '[defaults.scheduling_strategies]',
        'container_allocation = "spread"',
        '',
        '[defaults.error_handling]',
        'max_task_trials = 3',
        'dead_node_invalidation = false',
        '',
        '[defaults.authorization]',
        'num_login_attempts = 3',
        'block_for_seconds = 120',
        'tokens_valid_for_seconds = 172800',
        ''
    ]

    apache_file_lines = [
        '<VirtualHost *:80>',
        '    ProxyRequests Off',
        '    ProxyPass /cc http://localhost:8000',
        '    ProxyPassReverse /cc http://localhost:8000',
        '',
        '    DocumentRoot /opt/cc-ui',
        '    <Directory /opt/cc-ui>',
        '        Require all granted',
        '    </Directory>',
        '</VirtualHost>',
        ''
    ]

    c = _adapt_for_vagrant(
        d,
        port=cc_host_port,
        username=cc_username,
        password=cc_password,
        remote_input_data=remote_input_data,
        remote_result_data=remote_result_data
    )

    s = Stepper()
    readme_file_lines = []

    if not remote_input_data:
        readme_file_lines += [
            '',
            'STEP {}: It is required, that the input files listed below are copied to the appropriate file system '
            'locations before running the experiment:'.format(s.step())
        ]

        input_files_meta = c['meta_data']['input_files']
        for i, input_file in enumerate(input_files_meta):
            file_name = '{}.{}'.format(
                i + 1,
                c['meta_data']['input_files'][i]['file_extension_preference']
            )
            file_path = os.path.join(directories['input_files'], file_name)
            doc = input_file['doc']
            readme_file_lines += [
                '',
                'file doc: {}'.format(doc),
                'file location: {}'.format(file_path),
            ]

    readme_file_lines += [
        '',
        'STEP {}: Change to the {} directory and run:'.format(s.step(), output_directory),
        '',
        'vagrant up --provider virtualbox',
        '',
        'This will start a virtual machine, containing the Curious Containers execution engine. Vagrant and VirtualBox '
        'are required beforehand.',
        '',
        'STEP {}: Run the experiment from the generated JSON file:'.format(s.step()),
        '',
        'faice run experiment.json'
    ]

    if not remote_result_data:
        readme_file_lines += [
            '',
            'Result files will be stored in the {} directory.'.format(directories['result_files'])
        ]

    readme_file_lines += [
        '',
        'OPTIONAL: Access a graphical user interface to monitor the experiment progress via the following address in '
        'a browser:',
        '',
        'http://localhost:{}'.format(cc_host_port),
        'username: {}'.format(cc_username),
        'password: {}'.format(cc_password),
        '',
    ]

    # create files and directories
    files = [
        (vagrant_file_name, vagrant_file_lines),
        (provision_file_name, provision_file_lines),
        (cc_file_name, cc_file_lines),
        (apache_file_name, apache_file_lines),
        (readme_file_name, readme_file_lines)
    ]

    for file_name, file_lines in files:
        file_content = os.linesep.join(file_lines)
        file_path = os.path.join(output_directory, file_name)
        with open(file_path, 'w') as f:
            f.write(file_content)

    with open(os.path.join(output_directory, experiment_file_name), 'w') as f:
        json.dump(c, f, indent=4)

    credentials = {
        'username': cc_username,
        'password': cc_password,
        'is_admin': True
    }
    with open(os.path.join(output_directory, credentials_file_name), 'w') as f:
        json.dump(credentials, f, indent=4)

    for _, directory in directories.items():
        if not os.path.exists(directory):
            os.makedirs(directory)

    # print readme
    print_user_text(readme_file_lines)
