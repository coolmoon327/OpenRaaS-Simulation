# alpha v0.2

import traceback
import numpy as np
from .device import *
from .app import *
from .task import *
from .topology import *
from gym import spaces

def add_all_layers_of_app(device: Device, app: Application):
    totalsize = 0.
    if app not in device.apps:
        totalsize += app.size
    missing_layers = []
    for layer in app.env_layers:
        if layer not in device.layers:
            totalsize += layer.size
            missing_layers.append(layer)
        
    if totalsize <= device.mem:
        if app not in device.apps:
            device.store_data(app)
        for layer in missing_layers:
            device.store_data(layer)
        return True
    return False

class Environment(object):
    def __init__(self, config={}):
        self.devices: list[Device] = []       # first M devices are servers -> self.devices[0:M]
        self.workers: list[Device] = []
        # scheduled_tasks stores tasks delivered to workers (in execution ones), while new_tasks stores just generated ones in this slot
        # these two taks lists cannot store any tasks in common or out-of-lifetime ones
        self.scheduled_tasks: list[Task] = []
        self.new_tasks: list[Task] = []
        self.fs_candidates = [] # filestore worker candidates in a slot

        self.layerList = LayerList()
        self.appList = ApplicationList(self.layerList)
        
        # logs
        self.finished_tasks_qos = []    # [[start_delay, service_latency, speed, jilter], ...]

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
            if 'center' in self.cloud_model_type():
                self.topology.set_cloud()
        except:
            raise KeyError("Cannot find environment keys in config dict.")
        
        self.state_len = self.task_info_num+2+1+self.candidates_num*self.filestore_info_num
        self.generate_topology()
        self.reset()
    
    def reset(self):
        self.scheduled_tasks.clear()
        self.new_tasks.clear()
        self.fs_candidates.clear()

        self.finished_tasks_qos.clear()
        
        self.task_index = 0
        
        for device in self.devices:
            device.reset()
        
        self.topology.reset()
        
        self.next()
        state = self.get_state()
        while self.new_tasks[self.task_index].dropped:
            self.task_index += 1
            if self.task_index >= self.tasks_num:
                self.next()
            state = self.get_state()
        return state
    
    def seed(self, seed):
        np.random.seed(seed)
    
    def generate_topology(self):
        # In a RL game, maybe we should not reset the topology so that the agent can learn more potential details in its neu-network
        
        M, N = self.M, self.N
        
        self.devices.clear()
        self.workers.clear()
        self.topology.clear()
        
        # generate devices
        self.devices.clear()
        server_area_id = 0 if 'center' in self.cloud_model_type() else -1
        for i in range(M):
            device = Server(i)
            self.devices.append(device)
            self.topology.add_device(device, server_area_id)
            self.workers.append(device) # all servers are workers
        for j in range(N):
            i = M + j
            r = np.random.rand(0,3)
            if r == 0:
                device = Desktop(i)
            elif r == 1:
                device = MobileDevice(i)
            else:
                device = IoTDevice(i)
            device.task_type = self.config['task_type']
            self.devices.append(device)
            area_id = np.random.randint(1, self.topology.area_num) if server_area_id == 0 else -1
            self.topology.add_device(device, area_id)
            
            # change is_worker by config['worker_rate']
            device.is_worker = True if np.random.randint(0, 100)/100 < self.config['worker_rate'] else False
            
            if self.cloud_model_type() == "openraas" and device.is_worker:
                # only openraas allows a client to be a worker
                self.workers.append(device)
            

        if self.config['debug_mode']:
            self.topology.debug_mode = True
            self.topology.check_areas() # debug
            for device in self.devices:
                device.debug_mode = True
        
        # distribute layers & applications
        
        storage_app = self.appList.get_list(1)[0]
        if "raas" in self.cloud_model_type():
            ### resource as a service
            
            # 0. everyone can serve as the storage filestore
            for device in self.workers:
                if not device.isMobile:
                    device.store_data(storage_app)
            
            # 1. at least one server storing this data
            for List in [self.layerList, self.appList]:
                for data in List.get_list():
                    if storage_app == data:
                        continue
                        
                    ori = np.random.randint(0, M)
                    index = ori
                    while not self.workers[index].is_enough_for_storing(data):
                        index = index+1 if index < M-1 else 0
                        if index == ori:
                            # all M servers cannot store it, set error flag
                            raise ValueError(f"Data with id {data.id} cannot be stored in any a server!")
                    self.workers[index].store_data(data)    # host_id is appended in this method. if not, check it
                
            # 2. every worker has the chance to store some arbitrary data
            for device in self.workers:
                # a) average 10 data in a worker
                for List in [self.layerList, self.appList]:
                    if device.isMobile and List == self.appList:
                        continue
                    data_num = np.random.randint(1, 19)
                    for _ in range(data_num):   
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
        else:
            ### resource as a whole
            # don not care mobile or not
            
            # 1. at least one server storing this data
            List = self.appList
            for app in List.get_list():
                if app == storage_app:
                    continue
                
                ori = np.random.randint(0, M)
                index = ori
                worker = self.workers[index]
                while True:
                    if add_all_layers_of_app(worker, app):
                        break
                    index = index+1 if index < M-1 else 0
                    worker = self.workers[index]
                    if index == ori:
                        break
            
            # 2. every worker has the chance to store some arbitrary data
            for device in self.workers:
                add_all_layers_of_app(device, storage_app)
                
                # a) average 10 data in a worker
                data_num = np.random.randint(1, 19)
                for _ in range(data_num):
                    app = List.get_arbitrary_data()
                    ori = app.id
                    while True:
                        if device.id not in app.hosts:
                            if add_all_layers_of_app(device, app):
                                break
                        app = List.get_next_data(app)
                        if app.id == ori:
                            break
        
        if self.config['debug_mode']:
            # debug
            app_num = 0
            for d in self.devices[0:M]:
                app_num += len(d.apps)
            print(self.cloud_model_type(), "app_num (server)", app_num)
    
    def next(self):
        M, N = self.M, self.N
        
        if self.config['debug_mode']:
            # severely influence the performance, comment it after finishing debugging!!!
            for device in self.workers:
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
        for task in self.new_tasks:
            if task.app is None:
                task.app = self.appList.get_arbitrary_data(task.type)
            # task.app = self.appList.get_data_by_id(task.app_id)
        
        self.tasks_num = len(self.new_tasks)
        self.task_index = 0
        self.served_num = 0
            
    def get_state(self):
        def dropped_state(task):
            task.dropped = True
            return [-1. for _ in range(self.state_len)]
        self.fs_candidates = []
        task = self.new_tasks[self.task_index]  
        # 这里曾有超出 list range 的 bug，分析结果为 reset 时第一个 slot 内的任务被全部丢弃了
        # TODO: 丢弃率太高也是个问题，需要解决，目测和 edge 的 server_mem_rate 很低有关
        client = self.devices[task.user_id]
        
        # 4.1 find the closest worker as compute candidates
        target_c = -1
        minn = 1e6
        if task.bandwidth(0) <= client.bw:  # 这其实会导致 open 的丢弃率变高
            workers = []
            edge = self.topology.get_area_by_device(client)
            eds = [self.devices[did] for did in edge.devices]
            if "center" not in self.cloud_model_type() and self.config['compute_at_edge']:
                # 仅从边缘提供计算服务
                for ed in eds:
                    if ed.is_worker and not ed.isMobile and ed.isOpen:
                        if "raas" not in self.cloud_model_type() and ed.id not in task.app.hosts:
                            continue
                        workers.append(ed)
            else:
                # 计算服务可以来自任何地方
                for worker in self.workers:
                    if not worker.isMobile and worker.isOpen:
                        if "raas" not in self.cloud_model_type() and worker.id not in task.app.hosts:
                            continue
                        workers.append(worker)
            
            if workers.__len__() == 0:
                if "cache" in self.cloud_model_type():
                    # 遇到没有的服务，拒绝该请求，但会下载到该边缘的某个设备上
                    for ed in eds:
                        if add_all_layers_of_app(ed, task.app):
                            break
                return dropped_state(task)
            
            for device in workers:
                if device.id == task.user_id or (not device.check_task_availability(0, task)):
                    continue
                # if "raas" not in self.cloud_model_type():
                #     if task.app not in device.apps:
                #         # the traditional models ask the compute worker to be the only provider
                #         continue
                #     else:
                #         if task.mem > device.mem:
                #             # check_task_availability won't check storage tasks' mem for compute worker
                #             # but non-raas workers should have the availability
                #             continue
                
                if "raas" not in self.cloud_model_type() and task.mem > device.mem:
                    continue
                
                if task.type == 2:
                    link_bw = self.topology.get_link_states_between_devices(client, device)[0]
                    if link_bw < task.bandwidth(0):
                        continue
                
                s, l, _  = self.topology.get_link_states_between_devices_by_id(device.id, task.user_id)
                total_latency = l + task.mem / (s+1e6) * 1000.
                if total_latency < minn:
                    minn = total_latency
                # if -s < minn:
                #     minn = -s
                    target_c = device.id
        
        if target_c == -1:
            # print(f"Task require cpu={task.cpu} mem={task.mem} bw={task.bw if task.type==2 else None}, while max_cpu={np.max([worker.cpu if not worker.isMobile and worker.isOpen else 0. for worker in self.workers])} ") #max_mem={np.max([worker.mem for worker in self.workers])} max_bw={np.max([i.bw for worker in self.workers])}")
            return dropped_state(task)
        
        compute = self.devices[target_c]
        task.set_provider(0, target_c)
        task.missing_layers = compute.find_missing_layers(task)
        
        if "raas" not in self.cloud_model_type() and len(task.missing_layers):
            print(f"Missing {[task.missing_layers[i].id for i in range(len(task.missing_layers))]}, while having {[compute.layers[i].id for i in range(len(compute.layers))]}")
            raise ValueError(f"Cloud model {self.cloud_model_type()} chose a wrong compute worker {compute.id} lack of {len(task.missing_layers)} layers.")
        
        # 4.2 find devices with the target application as filestore candidates (return 10 candidates)
        # 4.2.1 finds all available devices
        avail_fs = []
        
        if task.type == 1 and self.config['public_data_deduplication'] and 'raas' in self.cloud_model_type():
            # 对于 public 的存储文件进行处理
            ds = self.workers if 'open' in self.cloud_model_type() else eds
            for i in reversed(range(len(task.files_id))):
                fid = task.files_id[i]
                if fid < 100 * self.config['public_data_rate']:
                    for d in ds:
                        if fid in d.caching_files_id:
                            task.mem -= task.files_mem[i]
                            del task.files_id[i]
                            del task.files_mem[i]
                            break
        
        if "raas" in self.cloud_model_type():
            for fs_id in task.app.hosts:
                device = self.devices[fs_id]
                
                if "edge" in self.cloud_model_type() and device not in eds:
                    # edge raas 只能在一个区域内进行组合
                    # center raas 默认 servers 只在 area 0，所以这里不用特殊判断
                    continue
                
                # 23-3-17: we only store app in inmobile devices
                # if device.isMobile:
                #     continue
                
                if device == client:
                    if device.bw < task.bandwidth(0) + task.bandwidth(1):
                        # client itself acts as the filestore worker
                        continue
                if device.check_task_availability(1, task):
                    if task.type == 2:
                        link_bw = self.topology.get_link_states_between_devices(compute, device)[0]
                        if link_bw < task.bandwidth(1):
                            continue
                        compute_area = self.topology.get_area_by_device(compute)
                        fs_area = self.topology.get_area_by_device(device)
                        if compute_area != fs_area:
                            if compute_area.backbone.bandwidth < task.bandwidth(0) + task.bandwidth(1):
                                continue
                    avail_fs.append(fs_id)
        else:
            avail_fs.append(target_c)
        
        if len(avail_fs) == 0:
            if "raas" in self.cloud_model_type() and self.config['raas_cache']:
                # 下载 missing app 到某个 filestore
                for worker in self.workers:
                    if not worker.isMobile:
                        if task.app not in worker.apps and task.app.size <= worker.mem:
                            worker.store_data(task.app)
                            break
            return dropped_state(task)
        elif len(avail_fs) > 1:
            # 4.2.2 calculate their priorities
            dict_p = {}
            for fs_id in avail_fs:
                line = self.topology.get_device_interface_link_by_id(fs_id)
                dict_p[fs_id] = line.bandwidth
            
            # 4.2.3 sort by priority and take the first 10 devices
            dict_p = dict(sorted(dict_p.items(), key=lambda item: -item[1]))
            self.fs_candidates = list(dict_p.keys()) if len(avail_fs) < 10 else list(dict_p.keys())[:10]
        else:
            # only one avail_fs
            self.fs_candidates = avail_fs
        
        # 4.3 find devicces with the target layers as depository candidates
        compute_link = self.topology.get_device_interface_link(compute)
        for layer_id in task.missing_layers:
            layer = self.layerList.get_data_by_id(layer_id)
            min_estimated_time = 1e6
            target_d = -1
            for d_id in layer.hosts:
                if layer in self.devices[d_id].layers:
                    link = self.topology.get_device_interface_link_by_id(d_id)
                    estimated_time = link.occupied_time + layer.size / (min(link.bandwidth, compute_link.bandwidth)+1e6) * 1000
                    if estimated_time < min_estimated_time:
                        target_d = d_id
                        min_estimated_time = estimated_time
            
            task.set_provider(2, target_d)
            
            if target_d == -1:
                # if none missing layer, won't get into this loop
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
                layer = self.layerList.get_data_by_id(task.missing_layers[index])
                link_latency = self.topology.get_link_states_between_devices(compute, depository)[1]
                begin_time = self.topology.get_link_occupied_time(compute, depository)
                duration = self.topology.cal_transmission_duration(compute, depository, layer.size)
                cd_latency = max(cd_latency, link_latency + begin_time + duration)
            
            start_delay = cd_latency
            
            if task.type == 1:
                # storage: forward
                speed = min(uc_speed, cf_speed)
                jilter = uc_jilter + cf_jilter
                service_latency = cf_latency + uc_latency + task.mem / (speed+1e-6) * 1000.
            else:
                speed = uc_speed
                jilter = uc_jilter
                service_latency = uc_latency
            
            self.finished_tasks_qos.append([start_delay, service_latency, speed, jilter])
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
                layer = self.layerList.get_data_by_id(task.missing_layers[index])
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
            if self.task_index >= self.tasks_num:
                new_slot = True
                self.next()
            
            state = self.get_state()
            is_dropped = self.new_tasks[self.task_index].dropped
            
        return state, reward, new_slot
    
    def cloud_model_type(self):
        cm = self.config['cloud_model']
        if cm == 0:
            return "openraas"
        elif cm == 1:
            return "center"
        elif cm == 2:
            return "center raas"
        elif cm == 3:
            return "edge"
        elif cm == 4:
            return "edge raas"
        elif cm == 5:
            return "edge cache"