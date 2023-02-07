import numpy as np
from .app import *

task_num = 0

class Task(object):
    def __init__(self, type, cpu, mem, user_id=-1, span=1):
        self.cpu = cpu
        self.mem = mem
        self.user_id = user_id
        self.type = type
        self.span = span
        
        global task_num
        self.id = task_num
        task_num += 1
        
        self.reset()
    
    def bandwidth(self, type):
        '''get bandwidth occupation
        input the microservice type number
        0: computation
        1: application files (meta OS)
        2: environment (image fetching)
        
        uplink and downlink are calculated together
        '''
        return 0
    
    def reset(self):
        self.app = ApplicationList.get_arbitrary_data()(self.type)
        self.providers = [-1, -1, -1]
        self.life_time = self.span  # the rest time slot it can survive on the cloud
    
    def step(self):
        self.life_time -= 1
        if self.life_time < 0:
            raise TimeoutError(f"The task {self.id} is out of date, but nobody deals with it!")
    
    def set_provider(self, microservice_type, provider_id):
        if 0 <= microservice_type < 4:
            self.providers[microservice_type] = provider_id
        else:
            raise ValueError(f"Input microservice_type {microservice_type} is out of range!")
    
    def get_provider(self, microservice_type):
        if 0 <= microservice_type < 4:
            return self.providers[microservice_type]
        else:
            raise ValueError(f"Input microservice_type {microservice_type} is out of range!")

class ProcessTask(Task):
    def __init__(self,  user_id=-1):
        cpu = max(20 + 3 * np.random.randn(1)[0], 0.)       # 11 ~ 29
        mem = max(5 + 1 * np.random.randn(1)[0], 0.)       # 2 ~ 8
        super().__init__(0, cpu, mem, user_id)


class StorageTask(Task):
    def __init__(self, user_id=-1):
        '''
        this task should give its storing time span
        different from others, its memory size will affect the filestore worker instead of the compute worker
        '''
        span = max(10 + 2 * np.random.randn(1)[0], 1.)        # 4 ~ 16 time slots (2h ~ 8h) existing on the cloud drive
        super().__init__(1, 0., 0., span)
        
        file_num = int(4 + np.random.randn(1)[0])            # 1 ~ 7 files
        self.storage_size = 0
        for i in range(file_num):
            self.storage_size += max(50 + 15 * np.random.randn(1)[0], 0.)       # 5 ~ 95 MB per file
        

class DesktopTask(Task):
    def __init__(self, user_id=-1):
        '''
        this task should give its lasting time span
        '''
        cpu = max(5 + 1.5 * np.random.randn(1)[0], 0.)       # 0.5 ~ 9.5
        span = max(3 + 1 * np.random.randn(1)[0], 1.)        # 1 ~ 6 time slots (30m ~ 3h) existing on the cloud drive
        super().__init__(2, cpu, 0., user_id, span)
        
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
        