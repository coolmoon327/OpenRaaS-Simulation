import multiprocessing as mp
import copy
import time
from packages.alg.engine import *
from packages.utils.utils import read_config
from packages.utils.logger import Logger

def run_simulation(config):
    # print(f"start simulation with N {config['N']}")
    engine = Engine(config)
    ret = engine.run_simulation()
    print(f"Finshed {config['M']}_{config['N']}_{config['cloud_model']}")
    # print(len(ret))
    return ret

def callback_simulation(x):
    print("=====All Finished=====")
    logger = Logger("results/openraas-simulation/simulation")
    for logs, conf in x:
        logger.scalars_summary("cahnge_N/drop_rate", {str(conf['cloud_model']): logs['drop_rate']}, conf['N'])
        logger.scalars_summary("cahnge_N/server_cpu_rate", {str(conf['cloud_model']): logs['server_cpu_rate']}, conf['N'])
        logger.scalars_summary("cahnge_N/server_mem_rate", {str(conf['cloud_model']): logs['server_mem_rate']}, conf['N'])
        logger.scalars_summary("cahnge_N/server_bw_rate", {str(conf['cloud_model']): logs['server_bw_rate']}, conf['N'])
        logger.scalars_summary("cahnge_N/worker_cpu_rate", {str(conf['cloud_model']): logs['worker_cpu_rate']}, conf['N'])
        logger.scalars_summary("cahnge_N/worker_mem_rate", {str(conf['cloud_model']): logs['worker_mem_rate']}, conf['N'])
        logger.scalars_summary("cahnge_N/worker_bw_rate", {str(conf['cloud_model']): logs['worker_bw_rate']}, conf['N'])

        logger.scalars_summary("cahnge_N/start_delay", {str(conf['cloud_model']): logs['start_delay']}, conf['N'])
        logger.scalars_summary("cahnge_N/service_latency", {str(conf['cloud_model']): logs['service_latency']}, conf['N'])
        logger.scalars_summary("cahnge_N/speed", {str(conf['cloud_model']): logs['speed']}, conf['N'])
        logger.scalars_summary("cahnge_N/jilter", {str(conf['cloud_model']): logs['jilter']}, conf['N'])

def test_openraas(config):
    pool = mp.Pool(32)
    
    # 1. change N
    configs = []
    # for N in range(1000, 20001, 1000):
    for N in range(100, 5101, 500):
        config['N'] = N
        for cloud_model in [0, 1, 3]:
        # for cloud_model in range(5):
        # for cloud_model in [1]:
            config['cloud_model'] = cloud_model
            configs.append(copy.deepcopy(config))
    
    pool.map_async(run_simulation, configs, callback=callback_simulation)
    pool.close()
    pool.join()

    # while True:
    time.sleep(1)

def debug(config):
    config['N'] = 100
    config['cloud_model'] = 1
    ret = run_simulation(config)
    print(ret)

if __name__ == "__main__":
    config = read_config('config.yml')
    
    test_openraas(copy.deepcopy(config))
    # debug(config)