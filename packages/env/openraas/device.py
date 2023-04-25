import numpy as np
from .task import *
from .app import *
import math

TASK_TYPE = 0


class Device(object):
    def __init__(self, id, cpu, mem, bw, isOpen, isMobile):
        self.id = id                # Identification number, should be unique
        self.capacity = [cpu, mem, bw]
        self.isOpen = isOpen        # Whether the operating system is open to developers or not
        self.isMobile = isMobile    # Whether the device is mobile or fixed
        
        self.layers: list[ContainerLayer] = []    # stored container layers
        self.timers = []    # timers of stored container layers
        self.default_timer = 5  # servers' timer is -1 so that they won't release layers
        self.apps: list[Application] = []      # tored app data
        
        self.req_tasks: list[ProcessTask] = [] # only used when it is a client
        self.new_tasks: list[ProcessTask] = []
        
        self.cal_tasks: list[ProcessTask] = []         # serve as a compute worker
        self.metaos_tasks: list[StorageTask] = []      # serve as a filestore worker
        self.image_tasks: list[DesktopTask] = []       # serve as a depository worker        
        self.reset()
        
        self.is_client = False
        self.is_worker = True
        self.worker_type = 0
        self.p_coef = [(np.random.randint(50, 100) / 100.), (np.random.randint(50, 100) / 100. / 1000.), (np.random.randint(50, 100) / 100.) ]  # p_coef = [0.5, 1]
        # TODO: design how to charge
        
        self.debug_mode = False
    
    def reset(self):
        # not reset layers & apps
        self.inner_cpu= 0. # self.capacity[0] * min(1., max(0., (0.5 + 0.15 * np.random.randn(1)[0])))
        self.cpu = self.capacity[0] - self.inner_cpu   # Spare computation capability: GigaFlops
        self.mem = self.capacity[1]             # Storage space for OpenRaaS: MegaBytes
        self.bw = self.capacity[2]              # bandwidth: MegaBytes
                                                # the remaining bandwidth only be considered in a desktop application scenario
                                                # other services only occupy network links for several seconds, which should be taken as the startup delay
        
        self.cal_tasks.clear()
        self.metaos_tasks.clear()
        self.image_tasks.clear()
    
        # List = ApplicationList
        # ids = self.apps
        # for _ in range(2):
        #     for id in ids:
        #         self.mem -= List.get_data_by_id(id).size
        #     List = LayerList
        #     ids = self.layers
        
        for data in self.layers+self.apps:
            self.mem -= data.size
    
    def step(self):
        '''step into next time slot'''
        # 1. clear instant cache of the last slot
        # don't clear tasks set here, because destop services may occupy several slots
        
        if False:
            # 2. update work load
            # be care the self.mem is prepared for OpenRaaS, and cannot be occupied by internal processes
            cpu_offset = self.capacity[0] * (0.1 * np.random.randn(1)[0])   # -0.3 ~ 0.3 of cpu capacity
            new_cpu = np.clip(self.cpu+cpu_offset, 0., self.capacity[0]-self.external_cpu_occupation())
            self.inner_cpu += self.cpu - new_cpu
            self.cpu = new_cpu
        else:
            pass
        
        if self.is_client:
            remove_list = []
            for i in range(self.timers.__len__()):
                self.timers[i] -= 1
                if self.timers[i] == 0:
                    # layer = LayerList.get_data_by_id(self.layers[i])
                    layer = self.layers[i]
                    remove_list.append(layer)
            for layer in remove_list:
                self.remove_layer(layer)
    
    def external_cpu_occupation(self):
        cpu = 0.
        for task in self.cal_tasks:
            cpu += task.cpu
        return cpu
    
    ### layer management
    def fetch_layer(self, layer):
        # check if the layer is missing
        if layer in self.layers:
            print(f"The layer {layer.id} exists in this device {self.id}.")
            return
        if self.mem < layer.size:
            raise ValueError(f"The layer {layer.id} size {layer.size} is larger than remain space {self.mem} of device {self.id}.")
        # add the missing layer into self repository
        self.layers.append(layer)
        self.timers.append(self.default_timer)
        layer.add_host(self.id)
        # resource changes
        self.mem -= layer.size
    
    def remove_layer(self, layer):
        if layer not in self.layers:
            raise ValueError(f"The layer {layer.id} does not exist in this device {self.id}.")
        i = self.layers.index(layer)
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
            if layer not in self.layers:
                ml.append(layer.id)
        return ml
    
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
        
        if task.type == 2:
            BW = 0
            if microservice_type == 0:
                BW = task.bandwidth(0) + task.bandwidth(1)
            elif microservice_type == 1:
                if self.id != task.get_provider(0):
                    BW = task.bandwidth(1)
            if BW > self.bw:
                return False
        
        if microservice_type == 0:
            if self.isMobile == True or self.isOpen == False or task.cpu > self.cpu:
                ans = False
            else:
                # remain env space check
                required_space = 0.
                if task.type != 1:
                    required_space += task.mem
                for layer in task.app.env_layers:
                    if layer not in self.layers:
                        required_space += layer.size
                if required_space > self.mem:
                    ans = False
        elif microservice_type == 1:
            if task.type == 1:
                # in a storage task, filestore worker is used to contain user upload data
                if self.isMobile == True or task.mem > self.mem:
                    ans = False
            # app check
            else:
                if task.app not in self.apps:
                    ans = False
        elif microservice_type == 2:
            # env layer check
            any_layer_existing = False
            for layer in task.app.env_layers:
                if layer in self.layers:
                    any_layer_existing = True
                    break
            if not any_layer_existing:
                ans = False
        else:
            raise ValueError(f"Input microservice_type {microservice_type} is out of range!")
        return ans
    
    def allocate_tasks(self, microservice_type, task, layer_id=-1):
        '''allocate task to this device, and specify its microservice character
        microservice_type is used to specify the identity of this device 
        0: the compute worker, and add the task into cal_tasks
        1: the filestore worker, and add the task into metaos_tasks
        2: the depository worker, and add the task into image_tasks
        '''

        if self.debug_mode:
            # Used for debugging
            if not self.check_task_availability(microservice_type, task):
                raise ValueError(f"The task with id {task.id} cannot be handled by device {self.id} in microservice_type {microservice_type}")
        
        tasks = self.get_tasks_set(microservice_type)
        tasks.append(task)
        
        # resource occupation
        if microservice_type == 0:
            self.cpu -= task.cpu
            if task.type != 1:
                # in a storage task, compute worker only forward user data
                self.mem -= task.mem
            # fetch layers
            for layer in task.app.env_layers:
                if layer.id in task.missing_layers:
                    self.fetch_layer(layer)
                else:
                    # self.refresh_layer_timers(layer=layer)
                    self.timers[self.layers.index(layer)] = self.default_timer
        
        elif microservice_type == 1:
            if task.type == 1:
                # in a storage task, filestore worker is used to contain user upload data
                self.mem -= task.mem

        elif microservice_type == 2:
            for i in range(len(self.layers)):
                if self.layers[i].id == layer_id:
                    local_index = i
                    break
            self.timers[local_index] = self.default_timer
    
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
        if microservice_type == 0:
            self.cpu += task.cpu
            if task.type != 1:
                self.mem += task.mem
        elif microservice_type == 1:
            if task.type == 1:
                # in a storage task, filestore worker is used to contain user upload data
                self.mem += task.mem
        # elif microservice_type == 2:
        #     pass
    
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
        if self.mem >= data.size:
            return True
        else:
            return False
    
    def store_data(self, data: Data):
        if not self.is_enough_for_storing(data):
            raise ValueError(f"Cannot store the input data {data.id}:{data.print_type()} in device {self.id}")
        self.mem -= data.size
        if data.type == -1:
            raise ValueError(f"Data with id {data.id} didn't set type value!")
        elif 10 <= data.type < 13:
            self.apps.append(data)
        else:
            self.layers.append(data)
            self.timers.append(self.default_timer)
        data.add_host(self.id)
    
    ## resource usage
    
    def idle_resource_occupation_rate(self, resource_type):
        if resource_type == 0:
            r = self.cpu
        if resource_type == 1:
            r = self.mem
        if resource_type == 2:
            r = self.bw
        return 1.-r/self.capacity[resource_type]
    
    def unit_price(self, resource_type):
        """
        0-cpu, 1-mem, 2-bandwidth
        """
        ocr = self.idle_resource_occupation_rate(resource_type)
        if ocr == 1:
            return 1e6
        return self.p_coef[resource_type] / (1 - ocr)
    
    def check_error(self):
        '''check whether the variables are correct
        return error_id
        0:  No problem
        -1:  Existing illegal data
        -2:  Device resource cannot match the capacity
        warning: only can check after finishing tasks schedule because of the req_tasks
        '''
        cpu = self.cpu + self.inner_cpu
        mem = self.mem
        bw = self.bw
        C = self.capacity
        
        # 1. check legality
        if not (0.<=round(cpu,6)<=C[0] and 0<=round(mem,6)<=C[1] and 0<=round(bw,6)<=C[2]):
            return -1
        
        # 2. check capacity
        # 2.1 external tasks
        for task in self.cal_tasks:
            cpu += task.cpu
            if task.type != 1:
                mem += task.mem
            bw += task.bandwidth(0)
            if self.id != task.get_provider(1):
                bw += task.bandwidth(1)
            if self.id not in task.get_provider(2):
                bw += task.bandwidth(2)
        for task in self.metaos_tasks:
            if self.id != task.get_provider(0):
                bw += task.bandwidth(1)
            if task.type == 1:
                mem += task.mem
        for task in self.image_tasks:
            if self.id != task.get_provider(0):
                bw += task.bandwidth(2)
        # as a client, it transfers data to the compute node
        for task in self.req_tasks:
            if not task.dropped:
                bw += task.bandwidth(0)
            
        # 2.2 stored applications & images
        # List = ApplicationList
        # ids = self.apps
        # for _ in range(2):
        #     for id in ids:
        #         mem += List.get_data_by_id(id).size
        #     List = LayerList
        #     ids = self.layers
        for data in self.apps+self.layers:
            mem += data.size
        
        if not(math.isclose(cpu, C[0], rel_tol=1e-10) and math.isclose(mem, C[1], rel_tol=1e-10) and math.isclose(bw, C[2], rel_tol=1e-10)):
            return -2
        return 0
    
    
class Server(Device):
    def __init__(self, id):
        cpu = 50.
        mem = 1e6
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
        self.is_worker = True if np.random.randint(0, 10) < 2 else False    # 20% to be a worker    # change in environment.py
        self.is_client = True
    
    def generate_task(self, task_type=-1):
        if task_type == -1:
            r = np.random.randint(0,100)    # 1:6:3
            if r < 10:
                task_type = 0
            elif r < 70:
                task_type = 1
            else:
                task_type = 2
            
        if task_type == 0:
            task = ProcessTask(self.id)
        elif task_type == 1:
            task = StorageTask(self.id)
        elif task_type == 2:
            task = DesktopTask(self.id, self.bw)
        self.new_tasks.append(task)
    
    def reset(self):
        super().reset()
        self.req_tasks.clear()
    
    def step(self):
        super().step()
        # generate new tasks
        self.new_tasks.clear()
        if np.random.randint(0,10) < 10:     # 100% chance to gain a new requirement
            self.generate_task(TASK_TYPE)


class Desktop(Client):
    def __init__(self, id):
        cpu = round(max(20 + 5 * np.random.randn(1)[0], 5.))      # 11 ~ 29
        mem = round(max(2e5 + 2e5 * np.random.randn(1)[0], 1e5))  # 21e3 ~ 39e3
        bw = round(max(300 + 70 * np.random.randn(1)[0], 10.))/8   # (90 ~ 510)/8 MBps
        isOpen = np.random.randint(0,10) < 9            # 90% devices are open
        isMobile = False
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
    
    def print_type(self):
        return 'desktop'


class MobileDevice(Client):
    def __init__(self, id):
        cpu = round(max(5 + 3 * np.random.randn(1)[0], 1.))       # 2 ~ 8
        mem = round(max(3e4 + 3e4 * np.random.randn(1)[0], 1e4))  # 4e3 ~ 16e3
        bw = round(max(300 + 70 * np.random.randn(1)[0], 10.))/8   # (90 ~ 510)/8 MBps
        isOpen = np.random.randint(0,10) < 3            # 30% devices are open
        isMobile = True
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
    
    def print_type(self):
        return 'mobile device'


class IoTDevice(Client):
    def __init__(self, id):
        cpu = round(max(5 + 3 * np.random.randn(1)[0], 1.))       # 2 ~ 8
        mem = round(max(1e4 + 2e4 * np.random.randn(1)[0], 1e4))   # 2e3 ~ 8e3
        bw = round(max(100 + 30 * np.random.randn(1)[0], 10.))/8   # (10 ~ 190)/8 MBps
        isOpen = np.random.randint(0,10) < 9            # 90% devices are open
        isMobile = np.random.randint(0,10) < 3          # 30% devices are mobile
        super().__init__(id, cpu, mem, bw, isOpen, isMobile)
    
    def print_type(self):
        return 'IoT device'