from faice.execution_engines import curious_containers, common_workflow_language
from faice.helpers import graceful_exception


ENGINES = {
    'curious-containers': curious_containers,
    'common-workflow-language': common_workflow_language
}


def get_engine(d):
    engine_type = d['execution_engine']['engine_type']
    return ENGINES[engine_type]


@graceful_exception('Could not run experiment.')
def run(d):
    engine = get_engine(d)
    engine.run(d)


@graceful_exception('Could not setup vagrant.')
def vagrant(d, output_directory, use_local_data):
    engine = get_engine(d)
    engine.vagrant(d, output_directory, use_local_data)
