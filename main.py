import multiprocessing as mp
import copy
import time
import os
from packages.alg.engine import *
from packages.utils.utils import read_config
from packages.utils.logger import Logger

def run_simulation(config):
    # print(f"start simulation with N {config['N']}")
    engine = Engine(config)
    ret = engine.run_simulation()
    print(f"Finshed {config['log_pretext']}_{config['M']}_{config['N']}_{config['cloud_model']}_{config['worker_rate']}")
    # print(len(ret))
    return ret

def callback_simulation(x):
    print("=====All Finished=====")
    logger = Logger("results/openraas-simulation/simulation")
    
    for logs, conf in x:
        if conf['log_pretext'] == 'change_N':
            step = conf['N']
            tag = str(conf['cloud_model'])
        if conf['log_pretext'] == 'change_worker_rate':
            step = conf['worker_rate']*10
            tag = str(conf['N'])
        
        logger.scalars_summary(f"{conf['log_pretext']}/drop_rate", {tag: logs['drop_rate']}, step)
        logger.scalars_summary(f"{conf['log_pretext']}/server_cpu_rate", {tag: logs['server_cpu_rate']}, step)
        logger.scalars_summary(f"{conf['log_pretext']}/server_mem_rate", {tag: logs['server_mem_rate']}, step)
        logger.scalars_summary(f"{conf['log_pretext']}/server_bw_rate", {tag: logs['server_bw_rate']}, step)
        logger.scalars_summary(f"{conf['log_pretext']}/worker_cpu_rate", {tag: logs['worker_cpu_rate']}, step)
        logger.scalars_summary(f"{conf['log_pretext']}/worker_mem_rate", {tag: logs['worker_mem_rate']}, step)
        logger.scalars_summary(f"{conf['log_pretext']}/worker_bw_rate", {tag: logs['worker_bw_rate']}, step)

        logger.scalars_summary(f"{conf['log_pretext']}/start_delay", {tag: logs['start_delay']}, step)
        logger.scalars_summary(f"{conf['log_pretext']}/service_latency", {tag: logs['service_latency']}, step)
        logger.scalars_summary(f"{conf['log_pretext']}/speed", {tag: logs['speed']}, step)
        logger.scalars_summary(f"{conf['log_pretext']}/jilter", {tag: logs['jilter']}, step)

def callback_error(error):
    print("=====Something wrong in executing=====")
    print(error)
    print("======================================")
    with open('error_log.txt', 'w') as f:
        f.write(time.ctime() + ':' + str(error) + '\n')

def test_openraas(config):
    pool = mp.Pool(32)
    
    configs = []
    
    if 1:
        if config['debug_mode']:
            step = 200
        else:
            step = 50
        # 1. change N
        config['log_pretext'] = 'change_N'
        # for N in range(1000, 20001, 1000):
        for N in range(100, 1501, step):
            config['N'] = N
            for cloud_model in [0, 2, 5, 3]:
            # for cloud_model in range(5):
            # for cloud_model in [1]:
                config['cloud_model'] = cloud_model
                configs.append(copy.deepcopy(config))
    
    if 0:
        # 2. change worker_rate
        config['log_pretext'] = 'change_worker_rate'
        config['cloud_model'] = 0
        for N in range(100, 1501, 300):
            config['N'] = N
            for x in range(0, 11, 1):
                config['worker_rate'] = x*1./10.
                configs.append(copy.deepcopy(config))
    
    pool.map_async(run_simulation, configs, callback=callback_simulation, error_callback=callback_error)
    pool.close()
    pool.join()

    # while True:
    time.sleep(1)

def debug(config):
    config['log_pretext'] = 'change_N'
    for cloud_model in [0, 1, 3]:
        # cloud_model = 0
        config['cloud_model'] = cloud_model
        for N in range(100, 1000, 100):
            # N = 1000
            config['N'] = N
            ret = run_simulation(config)
            print(ret)

def clear_logs():
    dir = "results/openraas-simulation/simulation"
    os.system(f"rm -rf {dir}/events.out.*")

if __name__ == "__main__":
    clear_logs()
    
    config = read_config('config.yml')
    
    test_openraas(copy.deepcopy(config))
    # debug(config)