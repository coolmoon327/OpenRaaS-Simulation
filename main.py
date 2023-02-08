from .alg.engine import *
from .utils.utils import read_config

if __name__ == "__main__":
    config = read_config('config.yml')
    engine = Engine(config)
    engine.run_simulation()