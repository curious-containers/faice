import os
import json
import jsonschema

from faice.schemas import experiment_schema
from faice.engines import get_engine


def validate(d):
    jsonschema.validate(d, experiment_schema)
    engine = get_engine(d)

    engine.validate_engine_config(d)
    engine.validate_instructions(d)
    engine.validate_meta_data(d)


def write_experiment_file(d, experiment_file):
    with open(os.path.expanduser(experiment_file), 'w') as f:
        json.dump(d, f, indent=4)
