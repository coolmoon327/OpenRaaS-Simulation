from distutils.command.clean import clean
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
        self.generate_topology()
        self.reset()
        self.reload_env_info()
    
    def reload_env_info(self, tasks_num=1):
        # State Design
        self.n_actions = tasks_num  # tasks number per step
        # self.observation_space = spaces.Tuple((spaces.Box(-1000., 1000., (1, self.task_info_num)),     
        #                                         # 1. tasks information
        #                                         spaces.Discrete(self.compute_type_num), spaces.Box(-1000., 1000., (1, 1)),           
        #                                         # 2. compute worker information: type (estimated by the global master), interface bandwidth
        #                                         spaces.Discrete(self.M+self.N),                
        #                                         # 3. total filestore candidates number
        #                                         spaces.Box(-1000., 1000., (1, self.filestore_info_num)) for _ in range(self.candidates_num))
        #                                         # 4. information of the top candidates_num priorities
        #                                        for __ in range(self.n_actions))    # (n_actions, ?)
        
        # Action Design: the selected index of given 10 filestores (for n_actions tasks)
        # Each step may change the n_actions (because the tasks number is dynamic in different slots), so dislike other envs, engine should check the space per step
        self.action_space = spaces.Tuple([spaces.Discrete(self.candidates_num) for _ in range(self.n_actions)]) # (n_actions)
    
    def generate_topology(self):
        # In a RL game, maybe we should not reset the topology so that the agent can learn more potential details in its neu-network
        
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
            for type in range(List.type_num):
                l = List.get_list(type)
                for data in l:
                    ori = np.random.randint(0, M)
                    index = ori
                    while (self.devices[index].id in data.hosts) and (not self.devices[index].is_enough_for_storing(data)):
                        index = index+1 if index < M-1 else 0
                        if index == ori:
                            # all M servers cannot store it, set error flag
                            raise ValueError(f"Data with id {data.id} cannot be stored in any a server!")
                    self.devices[index].store_data(data)    # host_id is appended in this method. if not, check it
            
        # 2. every device has a chance to store some arbitrary data
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
                    while timer and (device.id in data.hosts) and (not device.is_enough_for_storing(data)):
                        data = List.get_arbitrary_data()
                        timer -= 1
                    if (device.id not in data.hosts) and device.is_enough_for_storing(data):
                        device.store_data(data)
                        break   # success, jump out of the loop
                    
                    r2 = not r2
    
    def reset(self):
        self.scheduled_tasks.clear()
        self.new_tasks.clear()
        self.fs_candidates.clear()
        
        # self.topology.reset()
        # self.generate_topology()
    
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
                client = self.devices[task.user_id]
                compute = self.devices[task.get_provider(0)]
                filestore = self.devices[task.get_provider(1)]
                depositories = task.get_provider(2)
                
                compute.release_task(0, task)
                filestore.release_task(1, task)
                self.topology.release_between_devices(client, compute, task.bandwidth(0))
                self.topology.release_between_devices(compute, filestore, task.bandwidth(1))
                
                for d in depositories:
                    depository = self.devices[d]
                    depository.release_task(2, task)
                    self.topology.release_between_devices(compute, depository, task.bandwidth(3))
                
                # TODO: settle a bill
                pass
                
        for task in removed_tasks:
            self.scheduled_tasks.remove(task)
        
        # 4. collect new tasks from client devices
        for j in range(N):
            i = self.M + j
            self.new_tasks += self.devices[i].req_tasks
            
    def get_state(self):
        """
        Returns:
            state (np.array)
        """
        state = []
        minn = 1e6
        target_c = -1
        for task in self.new_tasks:
            # TODO: use a temp list to store bellow chosen workers, so that action & state need not containing the device ID
            # 4.1 find the closest devices as compute candidates
            edge_area = self.topology.areas[self.topology.device_to_area[task.user_id]]
            for device_id in edge_area.devices:
                device = self.devices[device_id]
                if device_id == task.user_id or not device.check_task_availability(0, task):
                    continue
                _, l, _  = self.topology.get_link_states_between_devices_by_id(device.id, task.user_id)
                if l < minn:
                    minn = l
                    target_c = device.id
            task.set_provider(0, target_c)
            
            # 4.2 find devices with the target application as filestore candidates (return 10 candidates)
            # 4.2.1 finds all available devices
            avail_fs =  task.app.hosts
            # 4.2.2 calculate their priorities
            # TODO: temporally use the interface latency to sort, modify it in need
            dict_p = {}
            for fs_id in avail_fs:
                line = self.topology.get_device_interface_link_by_id(fs_id)
                dict_p[fs_id] = line.bandwidth
            
            # 4.2.3 sort by priority and take the first 10 devices
            dict_p = dict(sorted(dict_p.items(), key=lambda item: -item[1]))
            all_candidates_num = len(avail_fs)
            prior_candidates = list(dict_p.keys()) if all_candidates_num < 10 else list(dict_p.keys())[:10]
            self.fs_candidates.append(prior_candidates)
            
            # 4.3 find devicces with the target layers as depository candidates
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
        
            # 4.4 arrange the observation
            task_info = [task.cpu, task.mem, task.span]
            # TODO: set the worker type
            worker_info = [0, self.topology.get_device_interface_link_by_id(target_c).bandwidth]
            candidates_info = [all_candidates_num]
            for fs_id in prior_candidates:
                interface = self.topology.get_device_interface_link_by_id(fs_id)
                candidates_info += [interface.bandwidth, interface.latency, interface.jilter]
            # padding
            i = all_candidates_num
            while i < self.candidates_num:
                i+=1
                candidates_info += [0., 0., 0.]
            
            if len(candidates_info) != 1 + self.candidates_num * self.filestore_info_num:
                raise ValueError(f"Candidates information number {len(candidates_info)} of task {task.id} does not equal to {1 + self.candidates_num * self.filestore_info_num}")
            
            state.append(task_info+worker_info+candidates_info)
        
        state = np.array(state)
        
        return state
    
    def step(self, action):
        if len(action) != len(self.new_tasks):
            raise ValueError(f"Action_space with length {len(action)} does not equal to the tasks number {len(self.new_tasks)}!")
        
        # TODO: add something about topology.occupied_time to estimate the real delay
        
        # 1. execute service composition
        for i in range(len(action)):
            task = self.new_tasks[i]
            
            if action[i] >= self.fs_candidates[i].__len__():
                continue
            
            task.set_provider(1, self.fs_candidates[i][action[i]])
            client = self.devices[task.user_id]
            
            if task.get_provider(0) == -1 or task.get_provider(1) == -1 or len(task.get_provider(2)) == 0 or task.bandwidth(0) > client.bw:
                # this task cannot be composed
                continue
            
            compute = self.devices[task.get_provider(0)]
            filestore = self.devices[task.get_provider(1)]
            depositories = task.get_provider(2)
            
            # resource changes
            compute.allocate_tasks(0, task) # TODO: we should pre-allocate resource for C and D! and release it no matter whether we execute it or not
            filestore.allocate_tasks(1, task)
            self.topology.transmit_between_devices(client, compute, task.bandwidth(0))
            self.topology.transmit_between_devices(compute, filestore, task.bandwidth(1))
            
            for d in depositories:
                depository = self.devices[d]
                depository.allocate_tasks(2, task) 
                self.topology.transmit_between_devices(compute, depository, task.bandwidth(3))
            
            # add newly executed ones in scheduled_tasks
            self.scheduled_tasks.append(task)
            
        # 2. enter next step and gain new states
        self.next()
        
        # 3. regenerate env info
        self.reload_env_info(self.new_tasks.__len__())
        
        # 4. get state data
        # state = self.get_state()
        
        # 5. return the new state
        # some task with long span cannot get instantaneous reward
        # TODO: maybe we should temporally store those state until its reward generated?
        # Or we settle its bill by estimation instead of waiting to finish the task
        
        # TODO: We should build a database to store the executing task info
        # 1. self.scheduled_tasks
        # 2. states before those tasks
        # 3. states after those tasks (randomly choose a task state in next slot)
        # 4. reward
        
        # return state