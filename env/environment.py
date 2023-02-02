import numpy as np
from .device import *

class Environment(object):
    def __init__(self, config):
        self.M = config['M']
        self.N = config['N']
        self.devices = []
        self.reset()
    
    def reset(self):
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
    
    def step(self):
        pass