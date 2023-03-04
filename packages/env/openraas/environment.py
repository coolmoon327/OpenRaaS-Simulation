# alpha v0.2

import numpy as np
from .device import *
from .app import *
from .task import *
from .topology import *
from gym import spaces

class Environment(object):
    def __init__(self, config={}):
        self.devices: list[Device] = []       # first M devices are servers -> self.devices[0:M]
        self.workers: list[Device] = []
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
        
        self.state_len = self.task_info_num+2+1+self.candidates_num*self.filestore_info_num
        self.generate_topology()
        self.reset()
    
    def reset(self):
        self.scheduled_tasks.clear()
        self.new_tasks.clear()
        self.fs_candidates.clear()
        
        self.task_index = 0
        
        for device in self.devices:
            device.reset()
        
        self.topology.reset()
        
        self.next()
        state = self.get_state()
        while self.new_tasks[self.task_index].dropped:
            self.task_index += 1
            state = self.get_state()
        return state
    
    def seed(self, seed):
        np.random.seed(seed)
    
    def generate_topology(self):
        # In a RL game, maybe we should not reset the topology so that the agent can learn more potential details in its neu-network
        
        # if want to simulate another cloud paradigm
        # 1. cloud-centric: use an area as remote cloud, clients there won't require any task
        # microservice composition is as usual but only executed in the remote cloud area
        # 2. totally edge: only use edge servers to provide microservices
        # before excution, the compute worker has to fetch application data instead of mounting them
        
        M, N = self.M, self.N
        
        self.devices.clear()
        self.workers.clear()
        self.topology.clear()
        
        # generate devices
        self.devices.clear()
        for i in range(M):
            device = Server(i)
            self.devices.append(device)
            self.topology.add_device(device)
            self.workers.append(device) # all servers are workers
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
            if device.is_worker:
                self.workers.append(device)

        self.topology.check_areas() # debug
        
        # distribute layers & applications
        
        # 0. everyone can serve as the storage filestore
        storage_app = ApplicationList.get_list(1)[0]
        for device in self.workers:
            device.store_data(storage_app)
        
        # 1. at least one server storing this data
        List = LayerList
        for _ in range(2):
            for type in range(List.type_num):
                l = List.get_list(type)
                for data in l:
                    if storage_app == data:
                        continue
                        
                    ori = np.random.randint(0, M)
                    index = ori
                    while not self.workers[index].is_enough_for_storing(data):
                        index = index+1 if index < M-1 else 0
                        if index == ori:
                            # all M servers cannot store it, set error flag
                            raise ValueError(f"Data with id {data.id} cannot be stored in any a server!")
                    self.devices[index].store_data(data)    # host_id is appended in this method. if not, check it
            List = ApplicationList
            
        # 2. every worker has the chance to store some arbitrary data
        for device in self.workers:
            # a) average 3 data in a client worker
            data_num = np.random.randint(1, 5)  
            for _ in range(data_num):
                # b) layer 80% or app 20%
                r2 = np.random.randint(0, 4)
                for _ in range(2):
                    if r2 == 0:
                        List = ApplicationList
                    else:
                        List = LayerList
                    # c) data
                    data = List.get_arbitrary_data()
                    ori = data.id
                    avai_flag = True
                    while (device.id in data.hosts) or (not device.is_enough_for_storing(data)):
                        data = List.get_next_data(data)
                        if data.id == ori:
                            avai_flag = False
                            break
                    if avai_flag:
                        device.store_data(data)
                        break   # success, jump out of the loop
                    
                    r2 = not r2
    
    def next(self):
        M, N = self.M, self.N
        
        for device in self.workers:
        # severely influence the performance, comment it after finishing debugging!!!
            err = device.check_error()
            if err != 0:
                raise ValueError(f"Error with tag {err} occurs in device {device.id}.")
        
        # 1. clear instant cache of the last slot
        self.new_tasks.clear() 
        self.fs_candidates.clear()
        
        # 2. update devices state
        for device in self.devices:
            device.step()
        
        self.topology.step()
        
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
                
                if task.type == 2:
                    self.topology.release_bandwidth_between_devices(client, compute, task.bandwidth(0))
                    self.topology.release_bandwidth_between_devices(compute, filestore, task.bandwidth(1))
                compute.release_task(0, task)
                filestore.release_task(1, task)
                client.req_tasks.remove(task)
                
                for d in depositories:
                    self.devices[d].release_task(2, task)
                
        for task in removed_tasks:
            self.scheduled_tasks.remove(task)
        
        # 4. collect new tasks from client devices
        for j in range(N):
            i = M + j
            self.new_tasks += self.devices[i].new_tasks
        
        self.tasks_num = len(self.new_tasks)
        self.task_index = 0
        self.served_num = 0
            
    def get_state(self):
        def dropped_state(task):
            task.dropped = True
            return [-1. for _ in range(self.state_len)]
        self.fs_candidates = []
        task = self.new_tasks[self.task_index]
        client = self.devices[task.user_id]
        
        # 4.1 find the closest worker as compute candidates
        target_c = -1
        if task.bandwidth(0) <= client.bw:
            minn = 1e6
            for device in self.workers:
                if device.id == task.user_id or (not device.check_task_availability(0, task)):
                    continue
                s, l, _  = self.topology.get_link_states_between_devices_by_id(device.id, task.user_id)
                total_latency = l + task.mem / (s+1e6) * 1000.
                if total_latency < minn:
                    minn = total_latency
                    target_c = device.id
        
        if target_c == -1:
            # print(f"Task require cpu={task.cpu} mem={task.mem} bw={task.bw if task.type==2 else None}, while max_cpu={np.max([worker.cpu if not worker.isMobile and worker.isOpen else 0. for worker in self.workers])} ") #max_mem={np.max([worker.mem for worker in self.workers])} max_bw={np.max([i.bw for worker in self.workers])}")
            return dropped_state(task)
        
        compute = self.devices[target_c]
        task.set_provider(0, target_c)
        task.missing_layers = compute.find_missing_layers(task)
        
        # 4.2 find devices with the target application as filestore candidates (return 10 candidates)
        # 4.2.1 finds all available devices
        avail_fs = []
        for fs_id in task.app.hosts:
            if self.devices[fs_id].check_task_availability(1, task):
                avail_fs.append(fs_id)
        
        # 4.2.2 calculate their priorities
        dict_p = {}
        for fs_id in avail_fs:
            line = self.topology.get_device_interface_link_by_id(fs_id)
            dict_p[fs_id] = line.bandwidth
        
        # 4.2.3 sort by priority and take the first 10 devices
        dict_p = dict(sorted(dict_p.items(), key=lambda item: -item[1]))
        self.fs_candidates = list(dict_p.keys()) if len(avail_fs) < 10 else list(dict_p.keys())[:10]
        
        # 4.3 find devicces with the target layers as depository candidates
        compute_link = self.topology.get_device_interface_link(compute)
        for layer_id in task.missing_layers:
            layer = LayerList.get_data_by_id(layer_id)
            min_estimated_time = 1e6
            target_d = -1
            for d_id in layer.hosts:
                if layer_id in self.devices[d_id].layers:
                    link = self.topology.get_device_interface_link_by_id(d_id)
                    estimated_time = link.occupied_time + layer.size / (min(link.bandwidth, compute_link.bandwidth)+1e6) * 1000
                    if estimated_time < min_estimated_time:
                        target_d = d_id
                        min_estimated_time = estimated_time
            
            task.set_provider(2, target_d)
            
            if target_d == -1:
                return dropped_state(task)
        
        # 4.4 arrange the observation
        task_info = [task.u_0(), task.qos[1], task.qos[2], task.qos[3]] # the scheduler only decides which filestore to choose, which is only influenced by delay, speed, and jilter
                                                                        # it also decides whether droping this task
        worker_info = [compute.worker_type, self.topology.get_device_interface_link(compute).bandwidth]
        candidates_info = [len(self.fs_candidates)]
        for fs_id in self.fs_candidates:
            interface = self.topology.get_device_interface_link_by_id(fs_id)
            candidates_info += [interface.bandwidth, interface.latency, interface.jilter]
        
        # padding
        i = len(self.fs_candidates)
        while i < self.candidates_num:
            i+=1
            candidates_info += [-1., -1., -1.]
        
        if len(candidates_info) != 1 + self.candidates_num * self.filestore_info_num:
            raise ValueError(f"Candidates information number {len(candidates_info)} of task {task.id} does not equal to {1 + self.candidates_num * self.filestore_info_num}")
        
        task.dropped = False
        state = np.array(task_info+worker_info+candidates_info)
        
        return state
    
    def step(self, action):
        # 1. execute service composition

        task = self.new_tasks[self.task_index]
        
        if not -1 <= action < len(self.fs_candidates):
            raise ValueError(f"Error action {action} is larger than the candidates number {len(self.fs_candidates)}")
        
        if action == -1 or task.dropped:
            # this task cannot be composed
            task.dropped = True
            reward = 0.
        else:
            fs_id = self.fs_candidates[action]
            task.set_provider(1, fs_id)
            
            client = self.devices[task.user_id]
            compute = self.devices[task.get_provider(0)]
            filestore = self.devices[fs_id]
            depositories = task.get_provider(2)
            
            # bidding
            # b-1 estimate utility
            uc_speed, uc_latency, uc_jilter = self.topology.get_link_states_between_devices(client, compute)
            cf_speed, cf_latency, cf_jilter = self.topology.get_link_states_between_devices(compute, filestore)
            cd_latency = 0.
            for index in range(len(depositories)):
                depository = self.devices[depositories[index]]
                layer = LayerList.get_data_by_id(task.missing_layers[index])
                link_latency = self.topology.get_link_states_between_devices(compute, depository)[1]
                begin_time = self.topology.get_link_occupied_time(compute, depository)
                duration = self.topology.cal_transmission_duration(compute, depository, layer.size)
                cd_latency = max(cd_latency, link_latency + begin_time + duration)
            
            start_delay = cd_latency
            if task.type == 0:
                service_latency = uc_latency
            elif task.type == 1:
                service_latency = cf_latency + uc_latency
            elif task.type == 2:
                service_latency = uc_latency
            
            speed = min(uc_speed, cf_speed)
            jilter = uc_jilter + cf_jilter
            
            utility = task.utility(start_delay, service_latency, speed, jilter)
        
            # b-2 estimate cost
            # should get unit price before allocation!!!
            c_price = compute.unit_price(0) * task.cpu + compute.unit_price(2) * (task.bandwidth(0) + task.bandwidth(1))
            fs_price = filestore.unit_price(2) * task.bandwidth(1)
            if task.type != 1:
                c_price += compute.unit_price(1) * task.mem
                # TODO: how to change the fs to use downloading volumn as the charge reference 
            else:
                fs_price += filestore.unit_price(1) * task.mem
            d_price = 0.
            for d in depositories:
                # d_price += self.devices[d].unit_price(2) * task.bandwidth(2)
                # TODO: how to charge by downloading
                pass
            
            cost = c_price + fs_price + d_price
            reward = utility - cost
            
            # resource changes
            compute.allocate_tasks(0, task) # we should pre-allocate resource for C and D! and release it no matter whether we execute it or not
            filestore.allocate_tasks(1, task)   # be careful sometimes the c is the f
            
            # image fetching should be fromer than file transmission
            for index in range(len(depositories)):
                depository = self.devices[depositories[index]]
                layer = LayerList.get_data_by_id(task.missing_layers[index])
                depository.allocate_tasks(2, task, layer.id)
                # self.topology.occupy_bandwidth_between_devices(compute, depository, task.bandwidth(2))
                # transmit images
                self.topology.transmit_task_between_devices(compute, depository, layer.size)
            
            # file transmission
            if task.type == 2:
                self.topology.occupy_bandwidth_between_devices(client, compute, task.bandwidth(0))
                self.topology.occupy_bandwidth_between_devices(compute, filestore, task.bandwidth(1))
            else:
                self.topology.transmit_task_between_devices(client, compute, task.mem)  # u -> c
                if task.type == 1:
                    self.topology.transmit_task_between_devices(compute, filestore, task.mem)   # u -> c -> f
            
            # add newly executed ones in scheduled_tasks
            self.scheduled_tasks.append(task)
            client.req_tasks.append(task)
            self.served_num += 1
        
        # 2. get state data
        is_dropped = True
        new_slot = False
        while is_dropped:
            self.task_index += 1
            # enter next step and gain new states
            if self.task_index == self.tasks_num:
                new_slot = True
                self.next()
            
            state = self.get_state()
            is_dropped = self.new_tasks[self.task_index].dropped
            
        return state, reward, new_slot