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
        
        self.dropped = False
        
        self.missing_layers = []
        
        self.reset()
    
    def reset(self):
        # self.app_id = -1 # np.random.randint(0, ApplicationList.app_num)
        self.app: Application = None  # inital in the Environment.next()
        self.providers = [-1, -1, []]
        self.life_time = self.span  # the rest time slot it can survive on the cloud
    
    def step(self):
        self.life_time -= 1
        if self.life_time < 0:
            raise TimeoutError(f"The task {self.id} is out of date, but nobody deals with it!")
    
    def u_0(self):
        qos = self.qos
        u_0 = qos[4] * self.span + qos[5] * self.mem + qos[6] * self.cpu
        return u_0
    
    def utility(self, start_delay, service_latency, speed, jilter):
        qos = self.qos
        ans = self.u_0() + qos[0] * start_delay + qos[1] * service_latency + qos[2] * speed + qos[3] * jilter
        return ans
    
    # def is_allocated(self):
    #     if self.get_provider(0) == -1 or self.get_provider(1) == -1:
    #         return False
    #     if len(self.missing_layers) and len(self.get_provider(2)) == 0:
    #         return False
    #     return True
    
    def bandwidth(self, type):
        return 0
    
    def set_QoS_weight(self, start_delay=1, service_latency=1, speed=-1, jilter=1, lifetime=-1, storage=-1, computation=-1):
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
        QoS[4]: serving time (positive, per slot)
        QoS[5]: data size (positive, per MB)
        QoS[6]: computation occupation (positive, per GF)
        '''
        if start_delay == 1:
            start_delay = -np.random.randint(1, 10)
        if service_latency == 1:
            service_latency = -np.random.randint(1, 10)
        if speed == -1:
            speed = np.random.randint(1, 5)
        if jilter == 1:
            jilter = -np.random.randint(1, 10)
        if lifetime == -1:
            lifetime = np.random.randint(10, 100)
        if storage == -1:
            storage = np.random.randint(1, 5)
        if computation == -1:
            computation = np.random.randint(10, 50)
        
        self.qos = [start_delay, service_latency, speed, jilter, lifetime, storage, computation]
    
    def set_provider(self, microservice_type, provider_id):
        if 0 <= microservice_type < 2:
            self.providers[microservice_type] = provider_id
        elif microservice_type == 2:
            # the index related to missing_layer
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

    def source_workers(self, image_id=-1, index=-1):
        if index == -1:
            index = self.missing_layers.index(image_id)
        return self.providers[2][index]

class ProcessTask(Task):
    def __init__(self,  user_id=-1):
        cpu = max(5 + 5 * np.random.randn(1)[0], .1)       # 5
        mem = 5 # max(5 + 1 * np.random.randn(1)[0], 0.) 
        super().__init__(0, cpu, mem, user_id)
        self.set_QoS_weight()


class StorageTask(Task):
    def __init__(self, user_id=-1):
        '''
        this task should give its storing time span
        different from others, its memory size will affect the filestore worker instead of the compute worker
        '''
        self.files_mem = []
        self.files_id = []
        span = round(max(5 + 2 * np.random.randn(1)[0], 1.))        # 5 time slots existing on the cloud drive
        # span = 1
        file_num = int(max(10 + 3 * np.random.randn(1)[0], 1.))          # 10 files
        mem = 0.
        for i in range(file_num):
            # file_mem = max(500 + 2000 * np.random.randn(1)[0], 10.)       # MB per file
            file_mem = 500
            file_id = np.random.randint(0, 99)
            while file_id in self.files_id: # 不重复
                file_id += 1
            self.files_id.append(file_id)
            self.files_mem.append(file_mem)
            mem += file_mem
        super().__init__(1, 0., mem, user_id, span)
        self.set_QoS_weight()


class DesktopTask(Task):
    def __init__(self, user_id=-1, bandwidth_maximum=1e6):
        '''
        this task should give its lasting time span
        '''
        cpu = max(5 + 10 * np.random.randn(1)[0], 0.1)       # 5
        span = round(max(1 + 3 * np.random.randn(1)[0], 1.))        # time slots existing on the cloud drive
        mem = max(1000 + 300 * np.random.randn(1)[0], 10.)
        # span = 1
        super().__init__(2, cpu, mem, user_id, span)
        self.set_QoS_weight()
        
        # self.bw = max(100 + 30 * np.random.randn(1)[0], 0.)/8       # (10 ~ 190)/8
        # self.bw = min(self.bw, bandwidth_maximum)
        self.bw = np.random.randint(1, max(2, min(100, int(bandwidth_maximum*8))*100)) / 100. / 8.
    
    def bandwidth(self, type):
        '''get bandwidth occupation
        input the microservice type number
        0: computation
        1: application files (meta OS)
        2: environment (image fetching)
        
        uplink and downlink are calculated together
        '''
        # bandwidth here only used to indicate the occupation of this slot
        if type == 0:
            return self.bw
        elif type == 1:
            # fixed 1 MBps
            return 1.
        elif type == 2:
            # TODO: deprecate it!
            return 0.
        