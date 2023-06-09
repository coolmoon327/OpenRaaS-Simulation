from .openraas.environment import *
import numpy as np

class EnvWrapper:
    def __init__(self, config={}):
        self.config = config
        self.env = Environment(config)
        
        self.episode_drop_rate = []
        # self.episode_worker_occupation = []
        # self.episode_server_occupation = []
        self.uesd_resource_server = [0., 0., 0.]
        self.total_resource_server = [0., 0., 0.,]
        self.uesd_resource_other = [0., 0., 0.]
        self.total_resource_other = [0., 0., 0.,]

    def reset(self):
        state = self.env.reset()
        
        self.episode_drop_rate.clear()
        # self.episode_worker_occupation.clear()
        # self.episode_server_occupation.clear()
        self.uesd_resource_server = [0., 0., 0.]
        self.total_resource_server = [0., 0., 0.,]
        self.uesd_resource_other = [0., 0., 0.]
        self.total_resource_other = [0., 0., 0.,]
        
        return state

    def seed(self, seed):
        self.env.seed(seed)
        
    def get_random_action(self):
        action = self.env.action_space.sample()
        return action

    def step(self, action):
        """step into next state with the input action executed

        Args:
            action (np.array)

        Returns:
            state (np.array)
        """
        # next_state, reward, terminal, _ = self.env.step(action.ravel())
        next_state, reward, enter_next_slot = self.env.step(action)
        if self.config['get_statistics']:
            self.statistic(enter_next_slot)
        return next_state, reward, enter_next_slot

    def set_random_seed(self, seed):
        self.env.seed(seed)

    def render(self):
        # frame = self.env.render(mode='rgb_array')
        # return frame
        pass

    def close(self):
        # self.env.close()
        pass

    def get_action_space(self):
        return self.env.action_space

    def normalise_state(self, state):
        return state

    def normalise_reward(self, reward):
        return reward
    
    def statistic(self, enter_next_slot=False):
        if enter_next_slot:
            self.episode_drop_rate.append(1-self.served_percent)
            # self.episode_worker_occupation.append(self.worker_occupation)
            # self.episode_server_occupation.append(self.server_occupation)
            
            if self.config['print_statistics_per_slot']:
                print(f"Serverd percent: {self.served_percent}, uesd resource of server: {self.uesd_resource_server}")
            
        env = self.env
        M = self.config['M']

        self.served_percent = env.served_num / env.tasks_num
        
        # occupation = [[],[],[]]
        for device in env.workers:
            for i in range(3):
                occupation_rate = device.idle_resource_occupation_rate(i)
                # occupation[i].append(occupation)
                if device.id < self.config['M']:
                    self.total_resource_server[i] += device.capacity[i]
                    self.uesd_resource_server[i] += device.capacity[i] * occupation_rate
                else:
                    doCensus = False
                    if i == 0 and not device.isMobile and device.isOpen:
                        doCensus = True
                    elif i == 1 and not device.isMobile:
                        doCensus = True
                    if doCensus:
                        self.total_resource_other[i] += device.capacity[i]
                        self.uesd_resource_other[i] += device.capacity[i] * occupation_rate
        
        # self.worker_occupation = [np.mean(occupation[0]), np.mean(occupation[1]), np.mean(occupation[2])]
        # self.server_occupation = [np.mean(occupation[0][:M]), np.mean(occupation[1][:M]), np.mean(occupation[2][:M])]
    
    def log_episode_statistics(self):
        logs = {}
        
        # worker_logs = np.array(self.episode_worker_occupation)
        # server_logs = np.array(self.episode_server_occupation)
        
        logs['drop_rate'] = np.mean(self.episode_drop_rate)
        # logs['worker_cpu_rate'] = np.mean(worker_logs[:, 0])
        # logs['worker_mem_rate'] = np.mean(worker_logs[:, 1])
        # logs['worker_bw_rate'] = np.mean(worker_logs[:, 2])
        # logs['server_cpu_rate'] = np.mean(server_logs[:, 0])
        # logs['server_mem_rate'] = np.mean(server_logs[:, 1])
        # logs['server_bw_rate'] = np.mean(server_logs[:, 2])
        logs['worker_cpu_rate'] = (self.uesd_resource_server[0] + self.uesd_resource_other[0]) / (self.total_resource_server[0] + self.total_resource_other[0])
        logs['worker_mem_rate'] = (self.uesd_resource_server[1] + self.uesd_resource_other[1]) / (self.total_resource_server[1] + self.total_resource_other[1])
        logs['worker_bw_rate'] = (self.uesd_resource_server[2] + self.uesd_resource_other[2]) / (self.total_resource_server[2] + self.total_resource_other[2])
        logs['server_cpu_rate'] = self.uesd_resource_server[0] / self.total_resource_server[0]
        logs['server_mem_rate'] = self.uesd_resource_server[1] / self.total_resource_server[1]
        logs['server_bw_rate'] = self.uesd_resource_server[2] / self.total_resource_server[2]

        # start_delay, service_latency, speed, jilter
        qos = np.array(self.env.finished_tasks_qos)
        logs['start_delay'] = np.mean(qos[:, 0])
        logs['service_latency'] = np.mean(qos[:, 1])
        logs['speed'] = np.mean(qos[:, 2])
        logs['jilter'] = np.mean(qos[:, 3])

        return logs