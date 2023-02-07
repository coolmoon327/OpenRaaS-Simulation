from msilib.schema import Error
import numpy as np
from .device import *
from .app import *
from .task import *

class Environment(object):
    def __init__(self, config):
        self.M = config['M']
        self.N = config['N']
        self.devices: list[Device] = []       # first M devices are servers -> self.devices[0:M]
        # scheduled_tasks stores tasks delivered to workers (in execution ones), while new_tasks stores just generated ones in this slot
        # these two taks lists cannot store any tasks in common or out-of-lifetime ones
        self.scheduled_tasks: list[Task] = []
        self.new_tasks: list[Task] = []
        
        self.reset()
    
    def reset(self):
        self.scheduled_tasks.clear()
        self.new_tasks.clear()
        
        M, N = self.M, self.N
        # generate devices
        self.devices.clear()
        for i in range(M):
            self.devices.append(Server(i))
        for j in range(N):
            i = self.M + j
            r = np.random.rand(0,3)
            if r == 0:
                self.devices.append(Desktop(i))
            elif r == 1:
                self.devices.append(MobileDevice(i))
            else:
                self.devices.append(IoTDevice(i))
    
        # distribute layers & applications
        # 1. at least one server storing this data
        List = LayerList
        for _ in range(2):
            for type in List.type_num:
                l = List.get_list(type)
                for data in l:
                    ori = np.random.randint(0, M)
                    index = ori
                    while not self.devices[index].is_enough_for_storing(data):
                        index = index+1 if index < M-1 else 0
                        if index == ori:
                            ori = -1    # all M servers cannot store it, set error flag
                            break
                    if ori == -1:
                        raise ValueError(f"Data with id {data.id} cannot be stored in any a server!")
                    self.devices[index].store_data(data)    # TODO: host_id is appended in this method. if not, check it
            List = ApplicationList
        # 2. every device has chance to store some arbitrary data
        for device in self.devices:
            while True:
                # a) chance
                r1 = np.random.randint(0, 10)
                if r1 > 3:   # 20%
                    break
                # b) layer or app
                r2 = np.random.randint(0, 2)
                for _ in range(2):
                    if r2 == 0:
                        List = LayerList
                    else:
                        List = ApplicationList
                    # c) data
                    data = List.get_arbitrary_data()
                    timer = 10  # random times
                    while timer and (device.id not in data.hosts) and (not device.is_enough_for_storing(data)):
                        data = List.get_arbitrary_data()
                        timer -= 1
                    if device.is_enough_for_storing(data):
                        device.store_data(data)
                        break   # success, jump out of the loop
                    else:
                        r2 = not r2
    
    def next(self):
        M, N = self.M, self.N
        
        # 1. clear instant cache of the last slot
        self.new_tasks.clear() 
        
        # 2. update devices state
        for device in self.devices:
            device.step()
        
        # 3. update exsiting tasks state
        # use a list to contain the global tasks, and device.py should not modify any value of a task
        removed_tasks = []
        for task in self.scheduled_tasks:
            task.step()
            if task.life_time == 0: # out of lifetime
                removed_tasks.append(task)
                for t in range(3):
                    device = self.devices[task.get_provider(t)]
                    device.release_task(t, task)
                    # TODO: settle a bill
                
        for task in removed_tasks:
            self.scheduled_tasks.remove(task)
        
        # 4. collect new tasks from client devices
        for j in range(N):
            i = self.M + j
            self.new_tasks += self.devices[i].req_tasks
    
    def step(self):
        # 1. execute service composition
        pass
        # add newly executed ones in scheduled_tasks
    
        # 2. enter next step and gain new states
        self.next()