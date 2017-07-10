import os
import json
import requests
import jsonschema
from copy import deepcopy
from pprint import pprint

from faice.helpers import find_open_port, print_user_text


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
    engine_config = d['execution_engine']['engine_config']
    jsonschema.validate(engine_config, _engine_config_schema)
    validated = True
    return validated


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

    if instructions.get('tasks'):
        raise Exception(
            'Using multiple Curious Containers tasks in instructions is not supported with FAICE.'
        )
    input_files = instructions['input_files']
    input_files_meta = d['meta_data']['input_files']
    if not isinstance(input_files_meta, list):
        raise Exception(
            'input_files in meta_data does not contain an array, but is required by Curious Containers execution '
            'engine.'
        )
    if len(input_files) != len(input_files_meta):
        raise Exception(
            'The number of input_files in instructions must be equals the number of input_files in meta_data'
        )
    for input_file in input_files_meta:
        if input_file['is_optional']:
            raise Exception(
                'input_files in meta_data cannot be marked as optional, because it is not supported by Curious '
                'Containers.'
            )

    result_files = instructions['result_files']
    result_files_meta = d['meta_data']['result_files']
    if not isinstance(result_files_meta, dict):
        raise Exception(
            'input_files in meta_data does not contain an object, but is required by Curious Containers execution '
            'engine.'
        )
    for result_file in result_files:
        local_result_file = result_file['local_result_file']
        if local_result_file not in result_files_meta:
            raise Exception(
                'result_file {} in instructions does not have a corresponding entry in results_files in meta_data.'
                ''.format(local_result_file)
            )

    if instructions_schema:
        return True
    return False


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


def _adapt_for_vagrant(d, port, use_local_data):
    c = deepcopy(d)

    c['execution_engine']['engine_config']['url'] = 'http://localhost:{}/cc'.format(port)
    c['execution_engine']['engine_config']['auth'] = {
        'username': 'user',
        'password': 'PASSWORD'
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
        'apt-get install -y curl git docker.io apache2',
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
        'cd ~/cc-server',
        'cp /vagrant/{} ./compose'.format(compose_file_name),
        'cp compose/config_samples/config.toml compose',
        'cp compose/config_samples/credentials.toml compose',
        'bash compose/scripts/create_systemd_unit_file -d $(pwd)',
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
        'echo',
        'echo setup successful',
        'echo "waiting for Curious Containers to finish initialization..."',
        'for i in {1..30}; do',
        '    http_code=$(curl -sL -w "%{http_code}" http://localhost:8000/ -o /dev/null)',
        '    if [ "${http_code}" == "200" ]; then',
        '        echo "initialization successfull"',
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
        '',
        '  cc-server-master:',
        '    build: ./cc-server-image',
        '    command: "python3 -u /root/.config/curious-containers/cc-server-master/init.py"',
        '    volumes:',
        '      - ../cc_server_master:/opt/cc_server_master:ro',
        '      - ../cc_commons:/opt/cc_commons:ro',
        '      - .:/root/.config/curious-containers:ro',
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
        '    command: "python3 -u /opt/cc_server_log"',
        '    volumes:',
        '      - ../cc_server_log:/opt/cc_server_log:ro',
        '      - ../cc_commons:/opt/cc_commons:ro',
        '      - .:/root/.config/curious-containers:ro',
        '      - /vagrant/curious-containers/logs:/root/.cc_server/logs',
        '    tty: true',
        '',
        '  mongo:',
        '    image: mongo',
        '    ports:',
        '      - "27017:27017"',
        '    volumes:',
        '      - /root/curious-containers/mongo/db:/data/db',
        '    tty: true',
        '',
        '  mongo-seed:',
        '    build: ./mongo-seed',
        '    volumes:',
        '      - .:/root/.config/curious-containers',
        '    command: "python3 -u /root/.config/curious-containers/mongo-seed/init.py"',
        '    links:',
        '      - mongo',
        '    tty: true',
        '',
        '  dind:',
        '    image: docker:dind',
        '    privileged: true',
        '    command: "dockerd --insecure-registry=registry:5000 -H tcp://0.0.0.0:2375"',
        '    volumes:',
        '      - /root/curious-containers/dind/docker:/var/lib/docker',
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
        '      - /vagrant/curious-containers/input_files:/root/input_files:ro',
        '      - /vagrant/curious-containers/result_files:/root/result_files',
        '    tty: true',
        '',
        '  registry:',
        '    image: registry:2',
        '    ports:',
        '      - "5000:5000"',
        '    environment:',
        '      REGISTRY_STORAGE_FILESYSTEM_ROOTDIRECTORY: /data',
        '    volumes:',
        '    - /root/curious-containers/registry/data:/data',
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

    c = _adapt_for_vagrant(d, port=cc_host_port, use_local_data=use_local_data)
    with open(os.path.join(output_directory, experiment_file_name), 'w') as f:
        json.dump(c, f, indent=4)

    addtional_directories = [
        os.path.join(output_directory, 'curious-containers', 'input_files'),
        os.path.join(output_directory, 'curious-containers', 'result_files'),
        os.path.join(output_directory, 'curious-containers', 'logs')
    ]

    for directory in addtional_directories:
        if not os.path.exists(directory):
            os.makedirs(directory)

    user_text = [
        '',
        'Change to the output directory and run:',
        '',
        'vagrant up --provider virtualbox',
        '',
        'This will start a virtual machine, containing the Curious Containers execution engine. Vagrant and VirtualBox '
        'are required beforehand.',
        '',
        'Go to the following address in a browser to access a graphical user interface:',
        '',
        'http://localhost:{}'.format(cc_host_port),
        'username: user',
        'password: PASSWORD'
    ]

    if use_local_data:
        user_text += [
            '',
            'The option --use-local-data has been set. It is required, that the input files listed below are copied '
            'to the appropriate file system locations before running the experiment:'
        ]

        input_files_meta = c['meta_data']['input_files']
        for i, input_file in enumerate(input_files_meta):
            file_name = 'file_{}'.format(i+1)
            file_path = os.path.join(output_directory, 'curious-containers', 'input_files', file_name)
            description = input_file['description']
            user_text += [
                '',
                'file description: {}'.format(description),
                'file location: {}'.format(file_path),
            ]

        result_file_directory = os.path.join(output_directory, 'curious-containers', 'result_files')
        user_text += [
            '',
            'When running the experiment, resulting files will be written to {}'.format(result_file_directory)
        ]

    user_text += [
        '',
        'In order to run the experiment in the virtual machine use faice as follows:',
        '',
        'faice run -f experiment.json'
    ]

    print_user_text(user_text)
