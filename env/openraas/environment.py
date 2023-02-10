import numpy as np
from .device import *
from .app import *
from .task import *
from .topology import *
from gym import spaces

class Environment(object):
    def __init__(self, config={}):
        self.devices: list[Device] = []       # first M devices are servers -> self.devices[0:M]
        # scheduled_tasks stores tasks delivered to workers (in execution ones), while new_tasks stores just generated ones in this slot
        # these two taks lists cannot store any tasks in common or out-of-lifetime ones
        self.scheduled_tasks: list[Task] = []
        self.new_tasks: list[Task] = []
        self.fs_candidates = [] # filestore worker candidates in a slot
    
        if len(config):
            self.load_config(config)
    
    def load_config(self, config):
        self.config = config
        try:
            self.M = config['M']
            self.N = config['N']
            self.candidates_num = config['candidates_num']    # candidates number per task
            self.task_info_num = config['task_info_num']
            self.compute_type_num = config['compute_type_num']
            self.filestore_info_num = config['filestore_info_num']
            self.topology = Topology(config['area_num'])
        except:
            raise KeyError("Cannot find environment keys in config dict.")
        self.reset()
        self.reload_env_info()()
    
    def reload_env_info(self, tasks_num=1):
        config = self.config
        # State Design
        self.n_actions = tasks_num  # tasks number per step
        self.observation_space = spaces.Tuple([[[spaces.Box(-100., 100., (self.task_info_num))],     # 1. tasks information
                                                [spaces.Discrete(self.compute_type_num)],            # 2. compute worker type (estimated by the global master)
                                                [spaces.Discrete(self.M+self.N)],                    # 3. total filestore candidates number
                                                [spaces.Box(-100., 100., (self.filestore_info_num)) for _ in range(self.candidates_num)]] # 4. the top candidates_num filestore candidates information
                                               for __ in range(self.n_actions)])    # (n_actions, 4, ?)
        
        # Action Design: the selected index of given 10 filestores (for n_actions tasks)
        # Each step may change the n_actions (because the tasks number is dynamic in different slots), so dislike other envs, engine should check the space per step
        self.action_space = spaces.Tuple([spaces.Discrete(self.candidates_num) for _ in range(self.n_actions)]) # (n_actions)
    
    def reset(self):
        self.scheduled_tasks.clear()
        self.new_tasks.clear()
        self.fs_candidates.clear()
        
        self.topology.reset()
        
        M, N = self.M, self.N
        # generate devices
        self.devices.clear()
        for i in range(M):
            device = Server(i)
            self.devices.append(device)
            self.topology.add_device(device)
        for j in range(N):
            i = self.M + j
            r = np.random.rand(0,3)
            if r == 0:
                device = Desktop(i)
            elif r == 1:
                device = MobileDevice(i)
            else:
                device = IoTDevice(i)
            self.devices.append(device)
            self.topology.add_device(device)

        self.topology.check_areas() # debug
        
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
                            # all M servers cannot store it, set error flag
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
                # b) layer 80% or app 20%
                r2 = np.random.randint(0, 4)
                for _ in range(2):
                    if r2 == 0:
                        List = ApplicationList
                    else:
                        List = LayerList
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
    
    def get_observation(self):
        for i in range(self.n_actions):
            # TODO: implement it
            pass
    
    def next(self):
        M, N = self.M, self.N
        
        # 1. clear instant cache of the last slot
        self.new_tasks.clear() 
        self.fs_candidates.clear()
        
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
                self.devices[task.get_provider(0)].release_task(0, task)
                self.devices[task.get_provider(1)].release_task(1, task)
                depositories = task.get_provider(2)
                for d in depositories:
                    self.devices[d].release_task(2, task)
                
                # TODO: settle a bill
                pass
                
        for task in removed_tasks:
            self.scheduled_tasks.remove(task)
        
        # 4. collect new tasks from client devices
        for j in range(N):
            i = self.M + j
            self.new_tasks += self.devices[i].req_tasks
    
    def step(self, action):
        if len(action) != len(self.new_tasks):
            raise ValueError(f"Action_space with length {len(action)} does not equal to the tasks number {len(self.new_tasks)}!")
        
        # 1. execute service composition
        for i in range(action):
            task = self.new_tasks[i]
            task.set_provider(1, self.fs_candidates[action[i]])
            if task.get_provider(0) == -1 or task.get_provider(1) == -1 or len(task.get_provider(2)) == 0:
                # this task cannot be composed
                continue
            # resource changes
            self.devices[task.get_provider(0)].allocate_tasks(0, task)
            self.devices[task.get_provider(1)].allocate_tasks(1, task)
            for d in task.get_provider(2):
                self.devices[d].allocate_tasks(1, task)  
            # add newly executed ones in scheduled_tasks
            self.scheduled_tasks.append(task)
            
        # 2. enter next step and gain new states
        self.next()
        
        # 3. regenerate env info
        self.reload_env_info(self.new_tasks.__len__())
        
        # 4. organize state data
        minn = 1e6
        target_c = -1
        for task in self.new_tasks:
            # TODO: use a temp list to store bellow chosen workers, so that action & state need not containing the device ID
            # 3.1 find the closest devices as compute candidates
            edge_area = self.topology.areas[self.topology.device_to_area[task.user_id]]
            for device in edge_area.devices:
                if device.id == task.user_id or not device.check_task_availability(0, task):
                    continue
                l = self.topology.cal_latency_between_devices_by_id(device.id, task.user_id)
                if l < minn:
                    minn = l
                    target_c = device.id
            task.set_provider(0, target_c)
            
            # 3.2 find devices with the target application as filestore candidates (return 10 candidates)
            pass
            # 3.2.1 finds all available devices
            # 3.2.2 calculate their priorities
            # 3.2.3 sort by priority and take the first 10 devices
            # TODO: implement it
        
            # 3.3 find devicces with the target layers as depository candidates
            # depository workers have two ways to choose: 1. all candidates 2. a target worker
            # if use the first one, we should modify the provider method of Task class
            missing_layers = self.devices[target_c].find_missing_layers(task)
            depositories = []
            for layer_id in missing_layers:
                layer = LayerList.get_data_by_id(layer_id)
                if len(layer.hosts) == 0:
                    # cannot execute this task because of layer lacking, dropping in the service compostion step
                    depositories = []
                    break
                depositories += layer.hosts
                # TODO: how about bandwidth?
            for d_id in depositories:
                task.set_provider(2, d_id)
            
        # 5. return the new state
        # some task with long span cannot get instantaneous reward
        # TODO: maybe we should temporally store those state until its reward generated?
        # Or we settle its bill by estimation instead of waiting to finish the task