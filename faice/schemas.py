_descriptions_array = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'description': {'type': 'string'},
            'is_optional': {'type': 'boolean'},
            'corresponding_instruction': {'type': 'string'}
        },
        'required': ['description', 'is_optional'],
        'addtionalProperties': False
    }
}

_descriptions_object = {
    'type': 'object',
    'patternProperties': {
        '^[a-zA-Z0-9._-]+$': {
            'type': 'object',
            'properties': {
                'description': {'type': 'string'},
                'is_optional': {'type': 'boolean'},
                'corresponding_instruction': {'type': 'string'}
            },
            'required': ['description', 'is_optional'],
            'additionalProperties': False
        }
    },
    'additionalProperties': False
}

experiment_schema_1 = {
    'type': 'object',
    'properties': {
        'format_version': {},
        'execution_engine': {
            'type': 'object',
            'properties': {
                'engine_type': {'enum': ['curious-containers', 'cwl-server']},
                'engine_config': {'type': 'object'}
            },
            'required': ['engine_type', 'engine_config'],
            'additionalProperties': False
        },
        'instructions': {'type': 'object'},
        'meta_data': {
            'type': 'object',
            'properties': {
                'applications': {
                    'type': 'object',
                    'patternProperties': {
                        '^[a-zA-Z0-9.:/-]+$': {
                            'type': 'object',
                            'properties': {
                                'app_type': {'enum': ['docker', 'commandline']},
                                'src_type': {'enum': ['git', 'hg', 'svn', 'cvs', 'bzr']},
                                'src_config': {'type': 'object'},
                                'build_type': {'enum': ['docker', 'make', 'cmake', 'script']},
                                'build_config': {'type': 'object'}
                            },
                            'required': ['src_type', 'src_config', 'build_type', 'build_config'],
                            'additionalProperties': False
                        }
                    },
                    'additionalProperties': False
                },
                'input_files': {
                    'oneOf': [
                        _descriptions_array,
                        _descriptions_object
                    ]
                },
                'result_files': {
                    'oneOf': [
                        _descriptions_array,
                        _descriptions_object
                    ]
                },
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'is_optional': {'type': 'boolean'},
                        'descriptions': {
                            'oneOf': [
                                _descriptions_array,
                                _descriptions_object
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
    },
    'required': ['format_version', 'execution_engine', 'instructions', 'meta_data'],
    'additionalProperties': False
}

experiment_schema = {
    'type': 'object',
    'properties': {
        'format_version': {'enum': ['1']}
    },
    'required': ['format_version'],
    'additionalProperties': True
}
