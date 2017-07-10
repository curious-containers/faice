from faice.execution_engines import curious_containers


ENGINES = {
    'curious-containers': curious_containers
}


def get_engine(d):
    engine_type = d['execution_engine']['engine_type']
    return ENGINES[engine_type]
