from faice.execution_engines import curious_containers, common_workflow_language


ENGINES = {
    'curious-containers': curious_containers,
    'common-workflow-language': common_workflow_language
}


def get_engine(d):
    engine_type = d['execution_engine']['engine_type']
    return ENGINES[engine_type]
