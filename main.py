import multiprocessing as mp
import copy
from packages.alg.engine import *
from packages.utils.utils import read_config

def run_simulation(config):
    # print(f"start simulation with N {config['N']}")
    engine = Engine(config)
    engine.run_simulation()

def test_openraas(config):
    threads = []
    
    # 1. change N from 500 to 2000
    for N in range(2000, 3001, 500):
        config['N'] = N
        for cloud_model in range(5):
            config['cloud_model'] = cloud_model
            t = mp.Process(target=run_simulation, args=(copy.deepcopy(config),))
            threads.append(t)

    # threads[0].start()
    # threads[0].join()
    
    # start
    for t in threads:
        t.start()
    
    # wait
    for t in threads:
        t.join()

if __name__ == "__main__":
    config = read_config('config.yml')
    
    test_openraas(copy.deepcopy(config))
    
    