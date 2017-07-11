import sys
import jsonschema
from ruamel.yaml import YAML

from faice.helpers import print_user_text


yaml = YAML()

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
        }
    },
    'required': ['cwl_file'],
    'additionalProperties': False
}

_meta_data_schema = {

}


def validate_engine_config(d):
    engine_config = d['execution_engine']['engine_config']
    jsonschema.validate(engine_config, _engine_config_schema)


def _load_cwl_file(d):
    pass


def validate_instructions(d):
    instructions = d['instructions']
    jsonschema.validate(instructions, _instructions_schema)


def validate_meta_data(d):
    meta_data = d['meta_data']
    jsonschema.validate(meta_data, _meta_data_schema)


def run(d):
    print_user_text([
        '',
        'The "faice run" tool is not available with the common-workflow-language execution engine. Try using '
        '"faice vagrant" instead.'
    ], error=True)
    sys.exit(1)


def vagrant(d, output_directory, use_local_data):
    pass
