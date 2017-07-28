doc_array_schema = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'doc': {'type': 'string'},
            'is_optional': {'type': 'boolean'},
        },
        'required': ['doc', 'is_optional'],
        'addtionalProperties': False
    }
}

doc_object_schema = {
    'type': 'object',
    'patternProperties': {
        '^[a-zA-Z0-9._-]+$': {
            'type': 'object',
            'properties': {
                'doc': {'type': 'string'},
                'is_optional': {'type': 'boolean'}
            },
            'required': ['doc', 'is_optional'],
            'additionalProperties': False
        }
    },
    'additionalProperties': False
}

src_code_schema = {
    'type': 'object',
    'properties': {
        'doc': {'type': 'string'},
        'repository_type': {'enum': ['git', 'hg', 'svn', 'cvs', 'bzr']},
        'repository_config': {'type': 'object'},
        'build_type': {'enum': ['docker', 'make', 'cmake', 'script']},
        'build_config': {'type': 'object'}
    },
    'required': ['doc'],
    'additionalProperties': False
}

experiment_schema = {
    'type': 'object',
    'properties': {
        'format_version': {'enum': ['1']},
        'execution_engine': {
            'type': 'object',
            'properties': {
                'engine_type': {'enum': ['curious-containers', 'common-workflow-language']},
                'engine_config': {'type': 'object'}
            },
            'required': ['engine_type', 'engine_config'],
            'additionalProperties': False
        },
        'instructions': {},
        'meta_data': {}
    },
    'required': ['format_version', 'execution_engine', 'instructions', 'meta_data'],
    'additionalProperties': False
}
