import numpy as np
from .device import *
from .app import *

class Environment(object):
    def __init__(self, config):
        self.M = config['M']
        self.N = config['N']
        self.devices = []
        self.reset()
    
    def reset(self):
        # generate devices
        self.devices.clear()
        for i in range(self.M):
            self.devices.append(Server[i])
        for j in range(self.N):
            i = self.M + j
            r = np.random.rand(0,3)
            if r == 0:
                self.devices.append(Desktop[i])
            elif r == 1:
                self.devices.append(MobileDevice[i])
            else:
                self.devices.append(IoTDevice[i])
    
        # distribute layers & applications
        
    
    def next(self):
        # 1. clear instant cache of the last slot
        pass 
        # 2. update devices state
        pass
        # 3. update exsiting tasks state
        # use a list to contain the global tasks, and device.py should not modify any value of a task
        pass
        # 4. collect new tasks from client devices
        pass
    
    def step(self):
        # 1. execute service composition
        pass
        # 2. enter next step and gain new states
        self.next()