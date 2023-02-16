import numpy as np
from .task import *
from .app import *

class Device(object):
    def __init__(self, id, cpu, mem, bw, isOpen, isMobile):
        self.id = id                # Identification number, should be unique
        self.capacity = [cpu, mem, bw]
        self.isOpen = isOpen        # Whether the operating system is open to developers or not
        self.isMobile = isMobile    # Whether the device is mobile or fixed
        
        self.layers = []    # IDs of stored container layers
        self.timers = []    # timers of stored container layers
        self.default_timer = 5  # servers' timer is -1 so that they won't release layers
        self.apps = []      # IDs of stored app data
        
        self.req_tasks = [] # only used when it is a client
        
        self.cal_tasks: list[ProcessTask] = []         # serve as a compute worker
        self.metaos_tasks: list[StorageTask] = []      # serve as a filestore worker
        self.image_tasks: list[DesktopTask] = []       # serve as a depository worker        
        self.reset()
    
    def reset(self):
        # not reset layers & apps
        self.cpu = self.capacity[0]             # Spare computation capability: GigaFlops
        self.mem = self.capacity[1]             # Storage space for OpenRaaS: MegaBytes
        self.bw = self.capacity[2]              # bandwidth: MegaBytes
                                                # the remaining bandwidth only be considered in a desktop application scenario
                                                # other services only occupy network links for several seconds, which should be taken as the startup delay
        self.preoccupied_resource = [0., 0., 0.]
        
        self.cal_tasks.clear()
        self.metaos_tasks.clear()
        self.image_tasks.clear()
    
    def step(self):
        '''step into next time slot'''
        # 1. clear instant cache of the last slot
        # don't clear tasks set here, because destop services may occupy several slots
        self.preoccupied_resource = [0., 0., 0.]
        
        # 2. update work load
        # be care the self.mem is prepared for OpenRaaS, and cannot be occupied by internal processes
        cpu_offset = self.capacity[0] * (0.03 +  0.03 * np.random.randn(1)[0])   # -0.06 ~ 0.12 of cpu capacity, more probability to be idle
        self.cpu = np.clip(self.cpu+cpu_offset, 0., self.capacity[0]-self.external_cpu_occupation())
        
        remove_list = []
        for i in range(self.timers.__len__()):
            self.timers[i] -= 1
            if self.timers[i] == 0:
                layer = LayerList.get_data_by_id(self.layers[i])
                remove_list.append(layer)
        for layer in remove_list:
            self.remove_layer(layer)
        
        # Warning: shouldn't update task here, because one task instance may be handled by three workers by weak copy. We should update it in the environment.py
        # # 3. update task state
        # for task in self.cal_tasks + self.metaos_tasks + self.image_tasks:
        #     task.step()
        #     if task.life_time == 0:
        #         # release expired tasks
        #         pass
        #         # billing
    
    def max_bandwidth(self):
        return self.capacity[2]   
    
    def external_cpu_occupation(self):
        cpu = 0.
        for task in self.cal_tasks:
            cpu += task.cpu
        return cpu
    
    ### layer management
    def fetch_layer(self, layer):
        # check if the layer is missing
        if layer.id in self.layers:
            print(f"The layer {layer.id} exists in this device {self.id}.")
            return
        if self.mem < layer.size:
            raise ValueError(f"The layer {layer.id} size {layer.size} is larger than remain space {self.mem} of device {self.id}.")
        # add the missing layer into self repository
        self.layers.append(layer.id)
        self.timers.append(self.default_timer)
        layer.add_host(self.id)
        # resource changes
        self.mem -= layer.size
    
    def remove_layer(self, layer):
        if layer.id not in self.layers:
            raise ValueError(f"The layer {layer.id} does not exist in this device {self.id}.")
        i = self.layers.index(layer.id)
        del self.layers[i]
        del self.timers[i]
        layer.remove_host(self.id)
        # resource changes
        self.mem += layer.size
    
    def check_layer_timeout(self):
        timeout_layer_index = []
        for i in range(self.timers.__len__()):
            if self.timers[i] == 0:
                # don't use <= 0, because servers' timers are negative and they don't release layers
                timeout_layer_index.append(i)
        return timeout_layer_index
    
    def find_missing_layers(self, task):
        ml = []
        for layer in task.app.env_layers:
            if layer.id not in self.layers:
                ml.append(layer.id)
        return ml
    
    # def refresh_layer_timers(self, layer=None, task=None):
    #     if task:
    #         for l in task.app.env_layers:
    #             if l.id in self.layers:
    #                 i = self.layers.index(l.id)
    #                 self.timers[i] = self.default_timer
    #     if layer:
    #         # if layer.id in self.layers:
    #         i = self.layers.index(layer.id)
    #         self.timers[i] = self.default_timer
    
    def push_layer(self, layer):
        if layer.id not in self.layers:
            raise ValueError(f"The layer {layer.id} does not exist in this device {self.id}.")
        # self.refresh_layer_timers(layer=layer)
        self.timers[self.layers.index(layer.id)] = self.default_timer
        # TODO: occupation calculation
        # We use all depositories working in the P2P file-sharing mode, so everyone only spends a piece of bandwidth
        # The details should be implemented in the environment.py
        pass
    
    ### tasks execution
    
    def get_tasks_set(self, microservice_type):
        if microservice_type == 0:
            return self.cal_tasks
        elif microservice_type == 1:
            return self.metaos_tasks
        elif microservice_type == 2:
            return self.image_tasks
        else:
            raise ValueError(f"Input microservice_type {microservice_type} is out of range!")
    
    def check_task_availability(self, microservice_type, task):
        '''check whether the task can be executed in this device with microservice_type'''
        ans = True
        if task.bandwidth(microservice_type) > self.bw  - self.preoccupied_resource[2]:
            return False
        if microservice_type == 0:
            if self.isMobile == True or self.isOpen == False or task.cpu > self.cpu  - self.preoccupied_resource[0] or task.mem > self.mem  - self.preoccupied_resource[1]:
                ans = False
            else:
                # remain env space check
                required_env_space = 0.
                for layer in task.app.env_layers:
                    if layer.id not in self.layers:
                        required_env_space += layer.size
                if required_env_space > self.mem - self.preoccupied_resource[1]:
                    ans = False
        elif microservice_type == 1:
            if task.type == 1:
                # in a storage task, filestore worker is used to contain user upload data
                if self.isMobile == True or task.storage_size > self.mem  - self.preoccupied_resource[1]:
                    ans = False
            # app check
            else:
                if task.app.id not in self.apps:
                    ans = False
        elif microservice_type == 2:
            # env layer check
            any_layer_existing = False
            for layer in task.app.env_layers:
                if layer.id in self.layers:
                    any_layer_existing = True
                    break
            if not any_layer_existing:
                ans = False
        else:
            raise ValueError(f"Input microservice_type {microservice_type} is out of range!")
        return ans
    
    def allocate_tasks(self, microservice_type, task):
        '''allocate task to this device, and specify its microservice character
        microservice_type is used to specify the identity of this device 
        0: the compute worker, and add the task into cal_tasks
        1: the filestore worker, and add the task into metaos_tasks
        2: the depository worker, and add the task into image_tasks
        '''
        tasks = self.get_tasks_set(microservice_type)
        if not self.check_task_availability(microservice_type, task):
            raise ValueError(f"The task with id {task.id} cannot be handled by device {self.id} in microservice_type {microservice_type}")
        tasks.append(task)
        
        # resource occupation
        # self.bw -= task.bandwidth(microservice_type) # now we occupy bandwidth in topology
        if microservice_type == 0:
            self.cpu -= task.cpu
            if task.type != 1:
                # in a storage task, compute worker only forward user data
                self.mem -= task.mem
            # fetch layers
            for layer in task.app.env_layers:
                if layer.id not in self.layers:
                    self.fetch_layer(layer)
                else:
                    # self.refresh_layer_timers(layer=layer)
                    self.timers[self.layers.index(layer.id)] = self.default_timer
        
        elif microservice_type == 1:
            if task.type == 1:
                # in a storage task, filestore worker is used to contain user upload data
                self.mem -= task.storage_size
        
        elif microservice_type == 2:
            # push layers
            for layer in task.app.env_layers:
                if layer.id in self.layers:
                    self.push_layer(layer=layer)
    
    def release_task(self, microservice_type, task):
        '''release a target task from list
        microservice_type is used to specify the identity of this device 
        0: the compute worker, and release the task from cal_tasks
        1: the filestore worker, and release the task from metaos_tasks
        2: the depository worker, and release the task from image_tasks
        '''
        tasks = self.get_tasks_set(microservice_type)
        try:
            tasks.remove(task)
        except:
            raise ValueError(f"No such task with id {task.id} in microservice_type {microservice_type}")
        # release resource occuptaion
        # self.bw += task.bandwidth(microservice_type)  # TODO: now we release bandwidth in topology
        if microservice_type == 0:
            self.cpu += task.cpu
            self.mem += task.mem
        elif microservice_type == 1:
            if task.type == 1:
                # in a storage task, filestore worker is used to contain user upload data
                self.mem += task.storage_size
        elif microservice_type == 2:
            pass
    
    def release_task_by_taskid(self, microservice_type, task_id):
        tasks = self.get_tasks_set(microservice_type)
        for task in tasks:
            if task.id == task_id:
                self.release_task(microservice_type, task)
        raise ValueError(f"No such task with id {task_id} in microservice_type {microservice_type}")
        
    def release_task_by_index(self, microservice_type, index):
        tasks = self.get_tasks_set(microservice_type)
        if not (0<=index<tasks.__len__()):
            raise IndexError(f"Task index of task {index} is out of range [0, {tasks.__len__()})!")
        self.release_task(tasks[index])
    
    ## data arrangement
    
    def is_enough_for_storing(self, data: Data):
        if self.mem > data.size:
            return True
        else:
            return False
    
    def store_data(self, data: Data):
        if not self.is_enough_for_storing(data):
            raise ValueError(f"Cannot store the input data in device {self.id}")
        self.mem -= data.size
        if data.type == -1:
            raise ValueError(f"Data with id {data.id} didn't set type value!")
        elif 10 <= data.type < 13:
            self.apps.append(data.id)
        else:
            self.layers.append(data.id)
            self.timers.append(self.default_timer)
        data.add_host(self.id)
    
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
        # as a client, it transfers data to the compute node
        for task in self.req_tasks:
            bw += task.bandwidth(0)
            
        # 2.2 stored applications & images
        List = ApplicationList
        ids = self.apps
        for _ in range(2):
            for id in ids:
                mem += List.get_data_by_id(id).size
            List = LayerList
            ids = self.layers
        
        if not(cpu == C[0] and mem == C[1] and bw == C[2]):
            return -2
        return 0
    
    
class Server(Device):
    def __init__(self, id):
        cpu = 50.
        mem = 3.2e6
        bw = 1e3/8
        isOpen = True
        isMobile = False
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
        self.default_timer = -1 # do not release any layer
    
    def print_type(self):
        return 'server'


class Client(Device):
    def __init__(self, id, cpu, mem, bw, isOpen, isMobile):
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
        
    # def set_requirement_type(self, type):
    #     '''set requirement type
    #     type=0: processing service (just like other computation offloading)
    #     type=1: storage service
    #     type=2: destop service
        
    #     TODO: add support for Internet APP (back-end simulation)
    #     '''
    #     self.req = type
    
    # def print_requirement_type(self):
    #     if self.req == 0:
    #         return 'processing'
    #     elif self.req == 1:
    #         return 'storage'
    #     elif self.req == 2:
    #         return 'destop'
    #     elif self.req == 3:
    #         return 'Internet'
    
    def required_tasks(self):
        return self.req_tasks
    
    def generate_task(self, task_type=-1):
        if task_type == -1:
            task_type = np.random.randint(0,3)
        if task_type == 0:
            task = ProcessTask(self.id)
        elif task_type == 1:
            task = StorageTask(self.id)
        elif task_type == 2:
            task = DesktopTask(self.id)
        self.preoccupied_resource[2] += task.bandwidth(0)
        self.req_tasks.append(task)
    
    def reset(self):
        super().reset()
        self.req_tasks.clear()
    
    def step(self):
        super().step()
        # generate new tasks
        self.req_tasks.clear()      # won't keep tasks waiting because the time slot unit is 30 minutes
        if np.random.randint(0,10) < 2:     # 20% chance to gain a new requirement
            self.generate_task()


class Desktop(Client):
    def __init__(self, id):
        cpu = max(20 + 3 * np.random.randn(1)[0], 0.)      # 11 ~ 29
        mem = max(30e3 + 3e3 * np.random.randn(1)[0], 0.)  # 21e3 ~ 39e3
        bw = max(300 + 70 * np.random.randn(1)[0], 0.)/8   # (90 ~ 510)/8 MBps
        isOpen = np.random.randint(0,10) < 3            # 30% devices are open
        isMobile = False
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
    
    def print_type(self):
        return 'desktop'


class MobileDevice(Client):
    def __init__(self, id):
        cpu = max(5 + 1 * np.random.randn(1)[0], 0.)       # 2 ~ 8
        mem = max(10e3 + 2e3 * np.random.randn(1)[0], 0.)  # 4e3 ~ 16e3
        bw = max(300 + 70 * np.random.randn(1)[0], 0.)/8   # (90 ~ 510)/8 MBps
        isOpen = False
        isMobile = True
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
    
    def print_type(self):
        return 'mobile device'


class IoTDevice(Client):
    def __init__(self, id):
        cpu = max(5 + 1 * np.random.randn(1)[0], 0.)       # 2 ~ 8
        mem = max(5e3 + 1e3 * np.random.randn(1)[0], 0.)   # 2e3 ~ 8e3
        bw = max(100 + 30 * np.random.randn(1)[0], 0.)/8   # (10 ~ 190)/8 MBps
        isOpen = True
        isMobile = np.random.randint(0,10) < 6          # 60% devices are mobile
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
    
    def print_type(self):
        return 'IoT device'