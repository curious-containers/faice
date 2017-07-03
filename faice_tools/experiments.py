import os
import sys
import json
import jsonschema

from faice_tools.schemas import experiment_schema, experiment_schema_1
from faice_tools.engines import get_engine


def validate_experiment(d):
    jsonschema.validate(d, experiment_schema)
    jsonschema.validate(d['experiment'], experiment_schema_1)
    engine = get_engine(d)
    validated = engine.validate_engine_config(d)
    if not validated:
        print('engine config schema could not be validated', file=sys.stderr)
    validated = engine.validate_instructions(d)
    if not validated:
        print('instructions schema could not be validated', file=sys.stderr)


def write_experiment_file(d, experiment_file):
    with open(os.path.expanduser(experiment_file), 'w') as f:
        json.dump(d, f, indent=4)
