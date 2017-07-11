import os
import sys
import json
import jsonschema
from traceback import format_exc

from faice.schemas import experiment_schema, experiment_schema_1
from faice.engines import get_engine
from faice.helpers import print_user_text


def validate_experiment(d):
    try:
        jsonschema.validate(d, experiment_schema)
        jsonschema.validate(d, experiment_schema_1)
        engine = get_engine(d)

        engine.validate_engine_config(d)
        engine.validate_instructions(d)
        engine.validate_meta_data(d)
    except:
        print(file=sys.stderr)
        print(format_exc(), file=sys.stderr)

        print_user_text([
            '',
            'Experiment validation failed. Examine the exception output above for details.'
        ], error=True)
        exit(1)

    print_user_text([
        '',
        'Experiment validation successful.'
    ])


def write_experiment_file(d, experiment_file):
    with open(os.path.expanduser(experiment_file), 'w') as f:
        json.dump(d, f, indent=4)
