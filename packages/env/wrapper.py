from .openraas.environment import *
import numpy as np

class EnvWrapper:
    def __init__(self, config={}):
        self.config = config
        self.env = Environment(config)
        
        self.episode_drop_rate = []
        self.episode_worker_occupation = []
        self.episode_server_occupation = []

    def reset(self):
        state = self.env.reset()
        
        self.episode_drop_rate.clear()
        self.episode_worker_occupation.clear()
        self.episode_server_occupation.clear()
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
        terminal = 0
        return next_state, reward, terminal

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
            self.episode_worker_occupation.append(self.worker_occupation)
            self.episode_server_occupation.append(self.server_occupation)
            
            if self.config['print_statistics_per_slot']:
                print(f"Serverd percent: {self.served_percent}, average worker occupation: {self.worker_occupation}")
            
        env = self.env
        M = self.config['M']

        self.served_percent = env.served_num / env.tasks_num
        
        occupation = [[],[],[]]
        for device in env.workers:
            for i in range(3):
                occupation[i].append(device.idle_resource_occupation_rate(i))
        
        self.worker_occupation = [np.mean(occupation[0]), np.mean(occupation[1]), np.mean(occupation[2])]
        self.server_occupation = [np.mean(occupation[0][:M]), np.mean(occupation[1][:M]), np.mean(occupation[2][:M])]
    
    def log_episode_statistics(self, logger):
        drop_rate = np.mean(self.episode_drop_rate)
        worker_cpu_rate = np.mean(self.episode_worker_occupation[:][0])
        worker_mem_rate = np.mean(self.episode_worker_occupation[:][1])
        worker_bw_rate = np.mean(self.episode_worker_occupation[:][2])
        server_cpu_rate = np.mean(self.episode_server_occupation[:][0])
        server_mem_rate = np.mean(self.episode_server_occupation[:][1])
        server_bw_rate = np.mean(self.episode_server_occupation[:][2])
        # print(f"{self.config['N']}, {self.config['cloud_model']}")
        # print(dropped_rate, worker_cpu_rate, server_cpu_rate, worker_mem_rate, server_mem_rate, worker_bw_rate, server_bw_rate)
        logger.scalar_summary(f"drop_rate/{self.config['cloud_model']}", drop_rate, self.config['N'])