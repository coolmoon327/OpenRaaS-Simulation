import numpy as np

class Task(object):
    def __init__(self, cpu, mem):
        self.cpu = cpu
        self.mem = mem
    
    def bandwidth(self, type):
        '''get bandwidth occupation
        input the microservice type number
        0: computation
        1: application files (meta OS)
        2: environment (image fetching)
        
        uplink and downlink are calculated together
        '''
        return 0
        

class ProcessTask(Task):
    def __init__(self):
        cpu = max(20 + 3 * np.random.randn(1)[0], 0.)       # 11 ~ 29
        mem = max(5 + 1 * np.random.randn(1)[0], 0.)       # 2 ~ 8
        super().__init__(cpu, mem)


class StorageTask(Task):
    def __init__(self):
        cpu = 0.
        file_num = int(4 + np.random.randn(1)[0])            # 1 ~ 7
        mem = 0
        for i in range(file_num):
            mem += max(50 + 15 * np.random.randn(1)[0], 0.)       # 5 ~ 95
        super().__init__(cpu, mem)


class DesktopTask(Task):
    def __init__(self):
        cpu = max(5 + 1.5 * np.random.randn(1)[0], 0.)       # 0.5 ~ 9.5
        mem = 0.
        super().__init__(cpu, mem)
        self.bw = max(100 + 30 * np.random.randn(1)[0], 0.)/8       # (10 ~ 190)/8
    
    def bandwidth(self, type):
        if type == 0:
            return self.bw + 1  # add the downlink bandwidth from metaOS
        elif type == 1:
            # fixed 1 MBps
            return 1
        else:
            # image fetching just like file downloading in other scenarios that cannot occupy the entire time slot 
            return 0