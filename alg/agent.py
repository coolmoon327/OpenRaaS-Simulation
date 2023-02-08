from ..env.wrapper import *
from ..utils.logger import Logger
from .sim.openraas_greedy import *

class SimulationAgent(object):
    def __init__(self, config, log_dir=''):
        self.config = config
        self.max_episodes = config["num_ep_train"]
        self.max_steps = config['max_ep_length']
        
        # Environment
        self.env_wrapper = EnvWrapper(config)
        
        # Algorithm
        self.alg = OPGreedy()
        
        # Logger
        log_path = f"{log_dir}/simulation"
        self.logger = Logger(log_path)
    
    def run(self):
        env = self.env_wrapper
        for episode in range(self.max_episodes):
            state = env.reset()
            
            for step in range(self.max_steps):
                # 1. modify state  
                pass
            
                # 2. gain action
                pass
            
                # 3. go into next step
                pass