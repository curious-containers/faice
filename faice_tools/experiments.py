import jsonschema

from faice_tools.schemas import experiment_schema, experiment_schema_1


def validate_experiment(e):
    jsonschema.validate(e, experiment_schema)
    jsonschema.validate(e['experiment'], experiment_schema_1)
