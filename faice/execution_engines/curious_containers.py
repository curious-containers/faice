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


def _adapt_for_vagrant(d, port, username, password, remote_data):
    c = deepcopy(d)

    c['execution_engine']['engine_config']['url'] = 'http://localhost:{}/cc'.format(port)
    c['execution_engine']['engine_config']['auth'] = {
        'username': username,
        'password': password
    }

    if not remote_data:
        if c['instructions'].get('tasks'):
            tasks = c['instructions']['tasks']
        else:
            tasks = [c['instructions']]
        for task in tasks:
            for i, input_file in enumerate(task['input_files']):
                input_file['connector_type'] = 'http'
                input_file['connector_access'] = {
                    'url': 'http://172.18.0.1:6000/{}.{}'.format(
                        i+1,
                        c['meta_data']['input_files'][i]['file_extension_preference']
                    ),
                    'method': 'GET'
                }

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
                        'url': 'http://172.18.0.1:6000/{}.{}'.format(
                            local_result_file,
                            c['meta_data']['result_files'][local_result_file]['file_extension_preference']
                        ),
                        'method': 'POST'
                    }
                }
                for local_result_file in local_result_files
            ]

    return c


def vagrant(d, output_directory, remote_data):
    engine_config = d['execution_engine']['engine_config']

    cc_server_version = engine_config['install_requirements']['cc_server_version']
    docker_compose_version = '1.14.0'

    cc_username = 'ccuser'
    cc_password = 'ccpass'
    cc_host_port = find_open_port()
    cc_guest_port = 80
    vm_memory = engine_config['install_requirements']['host_ram']
    vm_cpus = engine_config['install_requirements']['host_cpus']
    vm_box = 'trusty64'
    vm_box_url = 'https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-vagrant.box'
    vm_user = 'ubuntu'

    vagrant_file_name = 'Vagrantfile'
    provision_file_name = 'provision.sh'
    compose_file_name = 'docker-compose.yml'
    experiment_file_name = 'experiment.json'
    apache_file_name = 'cc-server.conf'
    credentials_file_name = 'cc-credentials.json'
    readme_file_name = 'README.txt'

    directories = {
        'input_files': os.path.join(output_directory, 'input_files'),
        'result_files': os.path.join(output_directory, 'result_files'),
        'logs': os.path.join(output_directory, 'curious-containers', 'logs')
    }

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
        'cp -R config_samples/config .',
        'bash bin/cc-create-systemd-unit-file -d $(pwd)',
        'systemctl enable cc-server',
        '',
        'docker-compose pull',
        'docker-compose build',
        '',
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
        '# user account for cc-server',
        'cd ~/cc-server',
        'pip3 install --user --upgrade -r requirements.txt',
        'cat /vagrant/{} | ~/cc-server/bin/cc-create-user-non-interactive '
        '-f ~/cc-server/compose/config/cc-server/config.toml -m localhost'.format(credentials_file_name),
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

    compose_file_lines = [
        'version: "2"',
        'services:',
        '  cc-server-web:',
        '    build: ./cc-server-image',
        '    command: "python3 -u -m cc_server.web_service"',
        '    ports:',
        '      - "8000:8000"',
        '    volumes:',
        '      - ./config/cc-server:/root/.config/cc-server:ro,z',
        '      - ../cc_server:/opt/cc_server:ro,z',
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
        '      - ./config/cc-server:/root/.config/cc-server:ro,z',
        '      - ../cc_server:/opt/cc_server:ro,z',
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
        '      - ./config/cc-server:/root/.config/cc-server:ro,z',
        '      - ../cc_server:/opt/cc_server:ro,z',
        '      - /vagrant/curious-containers/logs:/root/.cc_server/logs:rw,z',
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
        '      - ./config/cc-server:/root/.config/cc-server:ro,z',
        '      - ./mongo-seed/mongo_seed:/opt/mongo_seed:ro,z',
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
        '      - /root/.cc_server_compose/dind/docker:/var/lib/docker:rw,z',
        '    links:',
        '      - file-server',
        '    tty: true',
        '',
        '  file-server:',
        '    build: ./cc-server-image',
        '    command: "/root/.local/bin/gunicorn -w 1 -b 0.0.0.0:6000 file_server.__main__:app"',
        '    ports:',
        '      - "6000:6000"',
        '    volumes:',
        '      - ./file_server:/opt/file_server:ro,z',
        '      - /vagrant/input_files:/root/input_files:ro,z',
        '      - /vagrant/result_files:/root/result_files:rw,z',
        '    tty: true',
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
        d, port=cc_host_port, username=cc_username, password=cc_password, remote_data=remote_data
    )

    s = Stepper()
    readme_file_lines = []

    if not remote_data:
        readme_file_lines += [
            '',
            'STEP {}: The --remote-data flag has not been set. It is required, that the input files listed below '
            'are copied to the appropriate file system locations before running the experiment:'.format(s.step())
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
            'The result files will be written to the {} directory'.format(directories['result_files'])
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
        'faice run experiment.json',
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
        (compose_file_name, compose_file_lines),
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
