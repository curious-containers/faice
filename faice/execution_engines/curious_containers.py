import os
import json
import requests
import jsonschema
from copy import deepcopy
from pprint import pprint

from faice.helpers import print_user_text, Stepper
from faice.resources import find_open_port
from faice.schemas import src_code_schema, descriptions_array_schema, descriptions_object_schema


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
                'cc_server_version': {'enum': ['0.12']}
            },
            'required': ['cc_server_version'],
            'additionalProperties': False
        }
    },
    'required': ['url', 'auth', 'install_requirements'],
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
        'input_files': descriptions_array_schema,
        'result_files': descriptions_object_schema,
        'parameters': {
            'type': 'object',
            'properties': {
                'is_optional': {'type': 'boolean'},
                'descriptions': {
                    'oneOf': [
                        descriptions_array_schema,
                        descriptions_object_schema
                    ]
                }
            },
            'required': ['descriptions', 'is_optional'],
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
    url = engine_config['url'].rstrip('/')
    auth = (engine_config['auth']['username'], engine_config['auth']['password'])
    instructions_schema = None
    try:
        r = requests.get('{}/tasks/schema'.format(url), auth=auth)
        r.raise_for_status()
        instructions_schema = r.json()
    except:
        pass

    if instructions_schema:
        jsonschema.validate(instructions, instructions_schema)
    else:
        print_user_text([
            '',
            'Instructions could not be validated, because the corrisponding schema file could not be requested '
            'from cc-server.'
        ], error=True)

    if instructions.get('tasks'):
        raise Exception(
            'Using multiple Curious Containers tasks in instructions is not supported with FAICE.'
        )


def validate_meta_data(d):
    meta_data = d['meta_data']
    jsonschema.validate(meta_data, _meta_data_schema)

    instructions = d['instructions']

    if len(instructions['input_files']) != len(meta_data['input_files']):
        raise Exception(
            'The number of input_files in instructions must be equals the number of input_files in meta_data'
        )

    for input_file in meta_data['input_files']:
        if input_file['is_optional']:
            raise Exception(
                'input_files in meta_data cannot be marked as optional, because it is not supported by Curious '
                'Containers.'
            )

    for result_file in instructions['result_files']:
        local_result_file = result_file['local_result_file']
        if local_result_file not in meta_data['result_files']:
            raise Exception(
                'result_file {} in instructions does not have a corresponding entry in results_files in meta_data.'
                ''.format(local_result_file)
            )


def run(d):
    engine_config = d['execution_engine']['engine_config']
    instructions = d['instructions']
    url = engine_config['url'].rstrip('/')
    auth = (engine_config['auth']['username'], engine_config['auth']['password'])
    r = requests.post('{}/tasks'.format(url), auth=auth, json=instructions)
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


def _adapt_for_vagrant(d, port, username, password, use_local_data):
    c = deepcopy(d)

    c['execution_engine']['engine_config']['url'] = 'http://localhost:{}/cc'.format(port)
    c['execution_engine']['engine_config']['auth'] = {
        'username': username,
        'password': password
    }

    if use_local_data:
        if c['instructions'].get('tasks'):
            tasks = c['instructions']['tasks']
        else:
            tasks = [c['instructions']]
        for task in tasks:
            for i, input_file in enumerate(task['input_files']):
                input_file['connector_type'] = 'http'
                input_file['connector_access'] = {
                    'url': 'http://172.18.0.1:6000/file_{}'.format(i+1),
                    'method': 'GET'
                }

        if c['instructions'].get('tasks'):
            tasks = c['instructions']['tasks']
        else:
            tasks = [c['instructions']]

        for task in tasks:
            result_file_names = {result_file['local_result_file'] for result_file in task['result_files']}
            task['result_files'] = [
                {
                    'local_result_file': result_file_name,
                    'connector_type': 'http',
                    'connector_access': {
                        'url': 'http://172.18.0.1:6000/{}'.format(result_file_name),
                        'method': 'POST'
                    }
                }
                for result_file_name in result_file_names
            ]

    return c


def vagrant(d, output_directory, use_local_data):
    engine_config = d['execution_engine']['engine_config']

    cc_server_version = engine_config['install_requirements']['cc_server_version']
    docker_compose_version = '1.14.0'

    cc_username = 'ccuser'
    cc_password = 'ccpass'
    cc_host_port = find_open_port()
    cc_guest_port = 80
    vm_memory = 4096
    vm_cpus = 2
    vm_box = 'trusty64'
    vm_box_url = 'https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-vagrant.box'
    vm_user = 'ubuntu'

    vagrant_file_name = 'Vagrantfile'
    provision_file_name = 'provision.sh'
    compose_file_name = 'docker-compose.yml'
    experiment_file_name = 'experiment.json'
    apache_file_name = 'cc-server.conf'
    credentials_file_name = 'cc-credentials.json'

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
        'apt-get update',
        'apt-get install -y curl git docker.io apache2 python3-pip',
        '',
        '# docker and docker-compose',
        'usermod -aG docker {}'.format(vm_user),
        'curl -L https://github.com/docker/compose/releases/download/{}/docker-compose-$(uname -s)-$(uname -m) '
        '> /usr/local/bin/docker-compose'.format(docker_compose_version),
        'chmod +x /usr/local/bin/docker-compose',
        '',
        '# cc-server',
        'cd ~',
        'git clone -b {} --depth 1 https://github.com/curious-containers/cc-server.git'.format(cc_server_version),
        'cd cc-server/compose',
        'cp /vagrant/{} .'.format(compose_file_name),
        'cp config_samples/config.toml .',
        'bash bin/cc-create-systemd-unit-file -d $(pwd)',
        'systemctl enable cc-server',
        'systemctl start cc-server',
        '',
        '# cc-ui',
        'cd',
        'curl -sL https://deb.nodesource.com/setup_6.x | bash -',
        'apt-get install -y nodejs',
        'git clone --depth 1 https://github.com/curious-containers/cc-ui.git',
        'cd cc-ui',
        'touch src/config.js',
        'npm install',
        'npm update',
        'npm run build',
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
        'cd ~/cc-server',
        'pip3 install --user --upgrade -r requirements.txt',
        '',
        'echo',
        'echo setup successful',
        'echo "waiting for Curious Containers to finish initialization..."',
        'for i in {1..60}; do',
        '    http_code=$(curl -sL -w "%{http_code}" http://localhost:8000/ -o /dev/null)',
        '    if [ "${http_code}" == "200" ]; then',
        '        cat /vagrant/{} | ~/cc-server/bin/cc-create-user-non-interactive -f ~/cc-server/compose/config.toml '
        '-m localhost'.format(credentials_file_name),
        '        echo "initialization successful"',
        '        echo',
        '        echo Run the experiment from the generated JSON file:',
        '        echo faice run -f experiment.json',
        '        exit 0',
        '    fi',
        '    sleep 10',
        '    echo "still waiting ..."',
        'done',
        '',
        'echo "timeout: Curious Containers did not yet finish initialization"',
        ''
    ]

    compose_file_lines = [
        'version: "2"',
        'services:',
        '  cc-server-web:',
        '    build: ./cc-server-image',
        '    command: "python3 -u -m cc_server.web_service"',
        '    ports:',
        '      - "8000:8000"',
        '    volumes:',
        '      - ./config.toml:/root/.config/cc-server/config.toml:ro',
        '      - ../cc_server:/opt/cc_server:ro',
        '    links:',
        '      - mongo',
        '      - cc-server-master',
        '      - cc-server-log',
        '    tty: true',
        '',
        '  cc-server-master:',
        '    build: ./cc-server-image',
        '    command: "python3 -u -m cc_server.master_service"',
        '    volumes:',
        '      - ./config.toml:/root/.config/cc-server/config.toml:ro',
        '      - ../cc_server:/opt/cc_server:ro',
        '    links:',
        '      - mongo',
        '      - dind',
        '      - cc-server-log',
        '    depends_on:',
        '      - mongo-seed',
        '    tty: true',
        '',
        '  cc-server-log:',
        '    build: ./cc-server-image',
        '    command: "python3 -u -m cc_server.log_service"',
        '    volumes:',
        '      - ./config.toml:/root/.config/cc-server/config.toml:ro',
        '      - ../cc_server:/opt/cc_server:ro',
        '      - /vagrant/curious-containers/logs:/root/.cc_server/logs',
        '    tty: true',
        '',
        '  mongo:',
        '    image: mongo',
        '    ports:',
        '      - "27017:27017"',
        '    volumes:',
        '      - /root/.cc_server_compose/mongo/db:/data/db',
        '    tty: true',
        '',
        '  mongo-seed:',
        '    build: ./mongo-seed',
        '    volumes:',
        '      - ./config.toml:/root/.config/cc-server/config.toml:ro',
        '      - ./mongo-seed/mongo_seed:/opt/mongo_seed',
        '    command: "python3 -u -m mongo_seed"',
        '    links:',
        '      - mongo',
        '    tty: true',
        '',
        '  dind:',
        '    image: docker:dind',
        '    privileged: true',
        '    command: "dockerd --insecure-registry=registry:5000 -H tcp://0.0.0.0:2375"',
        '    volumes:',
        '      - /root/.cc_server_compose/dind/docker:/var/lib/docker',
        '    links:',
        '      - registry',
        '      - file-server',
        '    tty: true',
        '',
        '  file-server:',
        '    build: ./cc-server-image',
        '    command: "gunicorn -w 4 -b 0.0.0.0:6000 file_server.__main__:app"',
        '    ports:',
        '      - "6000:6000"',
        '    volumes:',
        '      - ./file_server:/opt/file_server:ro',
        '      - /vagrant/input_files:/root/input_files:ro',
        '      - /vagrant/result_files:/root/result_files',
        '    tty: true',
        '',
        '  registry:',
        '    image: registry:2',
        '    ports:',
        '      - "5000:5000"',
        '    environment:',
        '      REGISTRY_STORAGE_FILESYSTEM_ROOTDIRECTORY: /data',
        '    volumes:',
        '    - /root/.cc_server_compose/registry/data:/data',
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

    files = [
        (vagrant_file_name, vagrant_file_lines),
        (provision_file_name, provision_file_lines),
        (compose_file_name, compose_file_lines),
        (apache_file_name, apache_file_lines)
    ]

    for file_name, file_lines in files:
        file_content = os.linesep.join(file_lines)
        file_path = os.path.join(output_directory, file_name)
        with open(file_path, 'w') as f:
            f.write(file_content)

    c = _adapt_for_vagrant(
        d, port=cc_host_port, username=cc_username, password=cc_password, use_local_data=use_local_data
    )
    with open(os.path.join(output_directory, experiment_file_name), 'w') as f:
        json.dump(c, f, indent=4)

    credentials = {
        'username': cc_username,
        'password': cc_password,
        'is_admin': True
    }
    with open(os.path.join(output_directory, credentials_file_name), 'w') as f:
        json.dump(credentials, f, indent=4)

    directories = {
        'input_files': os.path.join(output_directory, 'input_files'),
        'result_files': os.path.join(output_directory, 'result_files'),
        'logs': os.path.join(output_directory, 'curious-containers', 'logs')
    }

    for _, directory in directories.items():
        if not os.path.exists(directory):
            os.makedirs(directory)

    s = Stepper()
    user_text = []

    if use_local_data:
        user_text += [
            '',
            'STEP {}: The option --use-local-data has been set. It is required, that the input files listed below '
            'are copied to the appropriate file system locations before running the experiment:'.format(s.step())
        ]

        input_files_meta = c['meta_data']['input_files']
        for i, input_file in enumerate(input_files_meta):
            file_name = 'file_{}'.format(i+1)
            file_path = os.path.join(directories['input_files'], file_name)
            description = input_file['description']
            user_text += [
                '',
                'file description: {}'.format(description),
                'file location: {}'.format(file_path),
            ]

        user_text += [
            '',
            'The result files will be written to the {} directory'.format(directories['result_files'])
        ]

    user_text += [
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
        'faice run -f experiment.json',
        '',
        'OPTIONAL: Access a graphical user interface to monitor the experiment progress via the following address in '
        'a browser:',
        '',
        'http://localhost:{}'.format(cc_host_port),
        'username: {}'.format(cc_username),
        'password: {}'.format(cc_password),
        '',
    ]

    print_user_text(user_text)
