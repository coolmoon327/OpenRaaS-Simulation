import numpy as np
import os
from datetime import datetime
from .agent import *

class Engine(object):
    def __init__(self, config):
        self.config = config
    
    def run_simulation(self):
        config = self.config
        
        # Create directory for experiment
        experiment_dir = f"{config['results_path']}/openraas-{datetime.now():%Y-%m-%d_%H:%M:%S}"
        if not os.path.exists(experiment_dir):
            os.makedirs(experiment_dir)
        
        # Create agent handling environment & algorithm
        agent = SimulationAgent(config, experiment_dir)
        
        agent.run()