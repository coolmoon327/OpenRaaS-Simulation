import numpy as np
from .app import *

task_num = 0

class Task(object):
    def __init__(self, type, cpu, mem, user_id=-1, span=1):
        # TODO: add QoS & billing method
        self.cpu = cpu
        self.mem = mem
        self.user_id = user_id
        self.type = type    # 0 1 2 - process storage desktop
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
        # TODO:  need checking & modifying
        return 0
    
    def set_QoS_weight(self, start_delay, service_latency, speed, ):
        '''
        QoS[0]: start-up delay (negative, per ms)
                influenced by the C-D link bandwidth (transition time)
        QoS[1]: service latency (negative, per ms)
                influenced by the Compute-Client link delay
        QoS[2]: upload & download speed (positive, per MBps)
                influenced by C-F the link bandwidth, and storage media (C or F depends on the task type)
                Note: assume we only know the interface states of devices instead of P2P link states
        QoS[3]: Jilter (negative, per jilter)
                influenced by the link between C-F, nobody knows the intermediate links' details
        QoS[3]: serving time (positive, per slot)
        QoS[4]: data size (positive, per MB)
        QoS[5]: computation occupation (positive, per GF)
        '''
        pass
    
    def reset(self):
        self.app = ApplicationList.get_arbitrary_data(self.type)
        self.providers = [-1, -1, []]
        self.life_time = self.span  # the rest time slot it can survive on the cloud
    
    def step(self):
        self.life_time -= 1
        if self.life_time < 0:
            raise TimeoutError(f"The task {self.id} is out of date, but nobody deals with it!")
    
    def set_provider(self, microservice_type, provider_id):
        if 0 <= microservice_type < 2:
            self.providers[microservice_type] = provider_id
        elif microservice_type == 2:
            self.providers[2].append(provider_id)
        else:
            raise ValueError(f"Input microservice_type {microservice_type} is out of range!")
    
    def get_provider(self, microservice_type):
        '''
        microservice_type=2 will return a list of depositories
        '''
        if 0 <= microservice_type < 3:
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
        span = round(max(10 + 2 * np.random.randn(1)[0], 1.))        # 4 ~ 16 time slots (2h ~ 8h) existing on the cloud drive
        super().__init__(1, 0., 0., user_id, span)
        
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
        span = round(max(3 + 1 * np.random.randn(1)[0], 1.))        # 1 ~ 6 time slots (30m ~ 3h) existing on the cloud drive
        super().__init__(2, cpu, 0., user_id, span)
        
        self.bw = max(100 + 30 * np.random.randn(1)[0], 0.)/8       # (10 ~ 190)/8
    
    def bandwidth(self, type):
        # bandwidth here only used to indicate the occupation of this slot
        if type == 0:
            return self.bw
        elif type == 1:
            # fixed 1 MBps
            return 1
        elif type == 2:
            # image fetching just like file downloading in other scenarios that cannot occupy the entire time slot 
            return 0 
        