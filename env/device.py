import imp
import numpy as np
from .task import *
from .topology import *

class Device(object):
    def __init__(self, id, cpu, mem, bw, isOpen, isMobile):
        self.id = id                # Identification number, should be unique
        self.capacity = [cpu, mem, bw]
        self.isOpen = isOpen        # Whether the operating system is open to developers or not
        self.isMobile = isMobile    # Whether the device is mobile or fixed
        self.cal_tasks = []         # serve as a compute worker
        self.metaos_tasks = []      # serve as a filestore worker
        self.image_tasks = []       # serve as a depository worker
        self.reset()
    
    def reset(self):
        self.cpu = self.capacity[0]             # Spare computation capability: GigaFlops
        self.mem = self.capacity[1]             # Storage space for OpenRaaS: MegaBytes
        self.bw = self.capacity[2]              # bandwidth: MegaBytes
                                                # the remaining bandwidth only be considered in a desktop application scenario
                                                # other services only occupy network links for several seconds, which should be taken as the startup delay
        self.cal_tasks.clear()
        self.metaos_tasks.clear()
        self.image_tasks.clear()
    
    def step(self):
        '''step into next time slot'''
        # 1. clear instant cache of the last slot
        
        # 2. update work load
        # be care the self.mem is prepared for OpenRaaS, and cannot be occupied by internal processes
        cpu_offset = self.capacity * (0.03 +  0.03 * np.random.randn(1)[0])   # -0.06 ~ 0.12 of cpu capacity, more probability to be idle
        self.cpu = np.clip(self.cpu+cpu_offset, 0., self.capacity[0]-self.external_cpu_occupation())
    
    def external_cpu_occupation(self):
        cpu = 0.
        for task in self.cal_tasks:
            cpu += task.cpu
        return cpu
    
    def release_task(self, task):
        pass
    
    def release_task_by_taskid(self, task_id):
        pass
    
    def check_error(self):
        '''check whether the variables are correct
        return error_id
        0:  No problem
        -1:  Existing illegal data
        -2:  Device resource cannot match the capacity
        '''
        cpu = self.cpu
        mem = self.mem
        bw = self.bw
        C = self.capacity
        # 1. check legality
        if not (0.<=cpu<=C[0] and 0<=mem<=C[1] and 0<=bw<=C[2]):
            return -1
        
        # 2. check capacity
        # 2.1 external tasks
        for task in self.cal_tasks:
            cpu += task.cpu
            mem += task.mem
            bw += task.bandwidth(0)
        for task in self.metaos_tasks:
            bw += task.bandwidth(1)
        for task in self.image_tasks:
            bw += task.bandwidth(2)
        # 2.2 stored applications & images
        pass
    
        return 0
    
    
class Server(Device):
    def __init__(self, id):
        cpu = 50.
        mem = 3.2e6
        bw = 1e3/8
        isOpen = True
        isMobile = False
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
    
    def type(self):
        return 'server'


class Client(Device):
    def __init__(self, id, cpu, mem, bw, isOpen, isMobile):
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
        
    def set_requirement(self, type_num):
        '''set requirement type
        type_num=0: processing service (just like other computation offloading)
        type_num=1: storage service
        type_num=2: destop service
        
        TODO: add support for Internet APP (back-end simulation)
        '''
        self.req = type_num
    
    def requirement(self):
        if self.req == 0:
            return 'processing'
        elif self.req == 1:
            return 'storage'
        elif self.req == 2:
            return 'destop'
        elif self.req == 3:
            return 'Internet'


class Desktop(Client):
    def __init__(self, id):
        cpu = max(20 + 3 * np.random.randn(1)[0], 0.)      # 11 ~ 29
        mem = max(30e3 + 3e3 * np.random.randn(1)[0], 0.)  # 21e3 ~ 39e3
        bw = max(300 + 70 * np.random.randn(1)[0], 0.)/8   # (90 ~ 510)/8 MBps
        isOpen = np.random.randint(0,10) < 3            # 30% devices are open
        isMobile = False
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
    
    def type(self):
        return 'desktop'


class MobileDevice(Client):
    def __init__(self, id):
        cpu = max(5 + 1 * np.random.randn(1)[0], 0.)       # 2 ~ 8
        mem = max(10e3 + 2e3 * np.random.randn(1)[0], 0.)  # 4e3 ~ 16e3
        bw = max(300 + 70 * np.random.randn(1)[0], 0.)/8   # (90 ~ 510)/8 MBps
        isOpen = False
        isMobile = True
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
    
    def type(self):
        return 'mobile device'


class IoTDevice(Client):
    def __init__(self, id):
        cpu = max(5 + 1 * np.random.randn(1)[0], 0.)       # 2 ~ 8
        mem = max(5e3 + 1e3 * np.random.randn(1)[0], 0.)   # 2e3 ~ 8e3
        bw = max(100 + 30 * np.random.randn(1)[0], 0.)/8   # (10 ~ 190)/8 MBps
        isOpen = True
        isMobile = np.random.randint(0,10) < 6          # 60% devices are mobile
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
    
    def type(self):
        return 'IoT device'