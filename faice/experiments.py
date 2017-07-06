import os
import sys
import json
import jsonschema
from traceback import format_exc

from faice.schemas import experiment_schema, experiment_schema_1
from faice.engines import get_engine
from faice.helpers import print_user_text


def validate_experiment(d):
    user_text_error = []
    try:
        jsonschema.validate(d, experiment_schema)
        jsonschema.validate(d['experiment'], experiment_schema_1)
        engine = get_engine(d)

        validated = engine.validate_engine_config(d)
        if not validated:
            user_text_error.append('Engine config schema could not be validated.')

        validated = engine.validate_instructions(d)
        if not validated:
            user_text_error.append('Instructions schema could not be validated.')

        print_user_text(user_text_error, error=True)
    except:
        print(format_exc(), file=sys.stderr)
        if user_text_error:
            user_text_error.append('')
        user_text_error.append('Experiment validation failed. Examine the exception output above for details.')

        print_user_text(user_text_error, error=True)
        exit(1)

    user_text = []
    if user_text_error:
        user_text.append('')
    user_text.append('Experiment validation successful.')

    print_user_text(user_text)


def write_experiment_file(d, experiment_file):
    with open(os.path.expanduser(experiment_file), 'w') as f:
        json.dump(d, f, indent=4)
